"""
Brighton Bikeshare Live Dashboard

A Flask web app that runs an ETL pipeline on Beryl's live GBFS feeds and
presents data-analysis results in the browser.

ETL:
  EXTRACT - pull station_status.json (live availability) and
            station_information.json (names, coords, capacity)
  TRANSFORM - merge on station_id, clean types, add derived columns
  LOAD   - append a timestamped snapshot to data/history.csv so we can
            analyse change over time

Analysis (rendered on the dashboard):
  - overall totals (bikes, docks, capacity, utilisation rate)
  - emptiest / fullest stations
  - per-station table with utilisation
  - change vs. the previous snapshot (bikes gained/lost per station)
"""

import os
import glob
from datetime import datetime, timezone

import pandas as pd
import requests
from flask import Flask, render_template

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GBFS_BASE = "https://beryl-gbfs-production.web.app/v2_2/Brighton"
STATION_STATUS_URL = f"{GBFS_BASE}/station_status.json"
STATION_INFO_URL = f"{GBFS_BASE}/station_information.json"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")

TIMEOUT_SECONDS = 20

app = Flask(__name__)


# ---------------------------------------------------------------------------
# ETL
# ---------------------------------------------------------------------------
def extract() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pull live status + static station info from the GBFS feeds."""
    status_resp = requests.get(STATION_STATUS_URL, timeout=TIMEOUT_SECONDS)
    status_resp.raise_for_status()
    status_df = pd.DataFrame(status_resp.json()["data"]["stations"])

    info_resp = requests.get(STATION_INFO_URL, timeout=TIMEOUT_SECONDS)
    info_resp.raise_for_status()
    info_df = pd.DataFrame(info_resp.json()["data"]["stations"])

    return status_df, info_df


def transform(status_df: pd.DataFrame, info_df: pd.DataFrame) -> pd.DataFrame:
    """Merge the two feeds and derive analysis-friendly columns."""
    # Keep only useful info columns
    info_cols = ["station_id", "name", "lat", "lon", "capacity"]
    info = info_df[info_df.columns.intersection(info_cols)].copy()

    # station_id types differ across feeds (int vs str) - normalise before merge
    status_df["station_id"] = status_df["station_id"].astype(str)
    info["station_id"] = info["station_id"].astype(str)

    df = status_df.merge(info, on="station_id", how="left")

    # Coerce types & clean
    for col in ["num_bikes_available", "num_docks_available", "capacity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # GBFS 2.1+ renamed bikes->vehicles; normalise if both absent
    if "num_bikes_available" not in df.columns and "num_vehicles_available" in df.columns:
        df["num_bikes_available"] = df["num_vehicles_available"]

    # Derived: total available points and utilisation
    df["total_capacity"] = df["num_bikes_available"] + df["num_docks_available"]
    df["bike_share"] = (
        df["total_capacity"].replace(0, 1)
    )  # avoid div-by-zero below
    df["utilisation_pct"] = (df["num_bikes_available"] / df["bike_share"] * 100).round(1)

    # Human-readable last-reported time
    df["last_reported_readable"] = pd.to_datetime(
        df["last_reported"], unit="s", utc=True
    ).dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    return df


def load(df: pd.DataFrame) -> None:
    """Append one timestamped snapshot row per station to history.csv."""
    os.makedirs(DATA_DIR, exist_ok=True)
    snapshot_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot = df[["station_id", "num_bikes_available", "num_docks_available"]].copy()
    snapshot.insert(0, "snapshot_time", snapshot_time)

    # Append (header only if the file doesn't exist yet)
    snapshot.to_csv(
        HISTORY_CSV,
        mode="a",
        index=False,
        header=not os.path.exists(HISTORY_CSV),
    )
    return snapshot_time


def run_etl() -> tuple[pd.DataFrame | None, str | None, str | None]:
    """Run the full pipeline. Returns (current_df, snapshot_time, error)."""
    try:
        status_df, info_df = extract()
        df = transform(status_df, info_df)
        snapshot_time = load(df)
        return df, snapshot_time, None
    except Exception as e:  # noqa: BLE001 - surface any feed/pipeline failure to the UI
        return None, None, str(e)


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------
def _read_previous_snapshot() -> pd.DataFrame | None:
    """Load the second-most-recent snapshot from history for change detection."""
    if not os.path.exists(HISTORY_CSV):
        return None
    history = pd.read_csv(HISTORY_CSV)
    times = history["snapshot_time"].unique()
    if len(times) < 2:
        return None
    prev_time = sorted(times)[-2]
    prev = history[history["snapshot_time"] == prev_time].copy()
    prev["station_id"] = prev["station_id"].astype(str)
    return prev[["station_id", "num_bikes_available"]]


def analyse(df: pd.DataFrame) -> dict:
    """Turn the current dataframe into a small dict of analysis results."""
    total_bikes = int(df["num_bikes_available"].sum())
    total_docks = int(df["num_docks_available"].sum())
    total_capacity = int(df["total_capacity"].sum())
    utilisation = round(total_bikes / total_capacity * 100, 1) if total_capacity else 0.0

    empty = df[df["num_bikes_available"] == 0]
    full = df[df["num_docks_available"] == 0]

    top_bikes = (
        df.sort_values("num_bikes_available", ascending=False)
        .head(5)[["name", "num_bikes_available"]]
        .to_dict(orient="records")
    )
    top_docks = (
        df.sort_values("num_docks_available", ascending=False)
        .head(5)[["name", "num_docks_available"]]
        .to_dict(orient="records")
    )

    rows = df[
        ["name", "station_id", "num_bikes_available", "num_docks_available",
         "utilisation_pct", "last_reported_readable"]
    ].sort_values("utilisation_pct", ascending=False).to_dict(orient="records")

    # Change vs previous snapshot
    prev = _read_previous_snapshot()
    change = None
    if prev is not None:
        merged = df[["station_id", "num_bikes_available", "name"]].merge(
            prev, on="station_id", suffixes=("", "_prev"), how="left"
        )
        merged["delta"] = merged["num_bikes_available"] - merged[
            "num_bikes_available_prev"
        ].fillna(0)
        change = {
            "gained": merged.sort_values("delta", ascending=False)
            .head(3)[["name", "delta"]].to_dict(orient="records"),
            "lost": merged.sort_values("delta", ascending=True)
            .head(3)[["name", "delta"]].to_dict(orient="records"),
        }

    return {
        "total_bikes": total_bikes,
        "total_docks": total_docks,
        "total_capacity": total_capacity,
        "utilisation": utilisation,
        "n_stations": len(df),
        "n_empty": len(empty),
        "n_full": len(full),
        "top_bikes": top_bikes,
        "top_docks": top_docks,
        "rows": rows,
        "change": change,
    }


@app.route("/")
def index():
    df, snapshot_time, error = run_etl()

    context = {
        "snapshot_time": snapshot_time,
        "error": error,
        "history_snapshots": _count_snapshots(),
    }
    if df is not None:
        context["analysis"] = analyse(df)
    return render_template("index.html", **context)


def _count_snapshots() -> int:
    if not os.path.exists(HISTORY_CSV):
        return 0
    try:
        return len(pd.read_csv(HISTORY_CSV, usecols=["snapshot_time"])[
            "snapshot_time"].unique())
    except Exception:  # noqa: BLE001
        return 0


if __name__ == "__main__":
    print("Starting Brighton Bikeshare dashboard on http://127.0.0.1:5000")
    app.run(debug=False, host="127.0.0.1", port=5000)