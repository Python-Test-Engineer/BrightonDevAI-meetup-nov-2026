# =====================================================================
# Brighton Bikeshare - Beryl GBFS Feed Reference & Data-to-CSV helpers
# =====================================================================
#
# Discovered at: https://beryl-gbfs-production.web.app/v2_2/Brighton/gbfs.json
# (the GBFS "auto-discovery" manifest). Each feed below is a JSON endpoint.
# Every one shares the same header: { "last_updated", "ttl", "version",
# "data": {...} }. The lines under each URL summarise WHAT it is, whether
# it is time-varying (changes during the day) and HOW to pull it to CSV.
#
# ----------------------------------------------------------------------
# 1) station_information.json   (static; ~119 stations)
#    What:   Names, lat/lon and dock capacity for every physical station
#            in the Brighton network. Row keys: capacity, lat, lon, name,
#            rental_uris, station_id.
#    Type:   STABLE reference data - changes rarely. Fetch once, cache.
#    -> data/ under the array "stations".
#
# 2) station_status.json        (live; ~119 stations)
#    What:   Realtime availability: bikes available, docks available,
#            is_installed/is_renting/is_returning, last_reported epoch.
#            This is the feed our ETL + forecast focus on.
#    Type:   TIME-VARYING - refreshes every ~120s. Poll regularly.
#    -> data/ under the array "stations".
#
# 3) free_bike_status.json      (live; ~862 vehicles)
#    What:   Free-floating / free-ranging vehicles (bikes, e-bikes and
#            scooters) with lat/lon, is_reserved, is_disabled,
#            current_range_meters. Some are docked at a station, some not.
#            This is a rich, constantly moving feed - poll alongside
#            station_status if you care about the full fleet, not just
#            docked bikes.
#    Type:   TIME-VARYING - refreshes continuously. Poll regularly.
#    -> data/ under the array "bikes".
#
# 4) vehicle_types.json         (static; 4 vehicle types)
#    What:   Catalogue of vehicle types - form_factor (bike/scooter/etc),
#            propulsion_type (electric/pedal), name, vehicle_type_id.
#    Type:   STABLE reference data.
#    -> data/ under the array "vehicle_types".
#
# 5) system_information.json    (static; 1 system)
#    What:   Operator metadata: name, operator, url, timezone, email,
#            phone_number, license_url, rental_apps. Not an array of
#            records - it is ONE object of system facts.
#    Type:   STABLE. More useful as a single saved blob than a table;
#            store it as one CSV row keyed on system_id.
#    -> data/ is the whole "data" object (single record).
#
# 6) system_pricing_plans.json  (static; 12 plans)
#    What:   Pricing plans - price, currency, per_min_pricing,
#            additional_fees, validity_interval, is_taxable, type.
#    Type:   STABLE reference data.
#    -> data/ under the array "plans".
#
# 7) system_regions.json        (static; 18 regions)
#    What:   Named areas used to group stations (name, region_id).
#            Useful to join onto station data for area-level analysis.
#    Type:   STABLE reference data.
#    -> data/ under the array "regions".
#
# 8) geofencing_zones.json      (static; ~1 zones polygon set)
#    What:   GeoJSON polygons defining where riding is allowed/forbidden
#            and speed limits. Not tabular; best saved as raw JSON/GeoJSON
#            rather than flattened to CSV.
#    Type:   STABLE but structured - preserve it as JSON.
#    -> data/ under "geofencing_zones".
#
# 9) gbfs_versions.json         (static; 2 versions)
#    What:   Lists the GBFS spec versions this publisher supports, and
#            the base URL for each. Mostly metadata for consumers.
#    Type:   STABLE.
#    -> data/ under the array "versions".
#
# ----------------------------------------------------------------------
# Builds:  pandas  requests   (run:  python data.py)
# Output:  writes <feed_name>.csv for every feed into ./data/
# Notes:   - Use json_normalize so nested columns (rental_uris, pricing)
#            flatten into usable CSV columns.
#           - geofencing_zones is kept as raw JSON - GeoJSON does not
#             flatten meaningfully to a rectangular table.
# =====================================================================

import json
import os
from os.path import abspath, dirname, join

import pandas as pd
import requests

GBFS_BASE = "https://beryl-gbfs-production.web.app/v2_2/Brighton"
HERE = dirname(abspath(__file__))
DATA_DIR = join(HERE, "data")

# feed name -> (JSON array key to export; None = export whole data object)
FEEDS = {
    "station_information": "stations",
    "station_status": "stations",
    "free_bike_status": "bikes",
    "vehicle_types": "vehicle_types",
    "system_pricing_plans": "plans",
    "system_regions": "regions",
    "gbfs_versions": "versions",
    "system_information": None,
}


def fetch_json(url: str) -> dict:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def feed_to_df(feed_name: str, arr_key):
    """Pull one feed and flatten the relevant array into a DataFrame."""
    url = f"{GBFS_BASE}/{feed_name}.json"
    print(f"[fetch] {feed_name}.json ...", end=" ")
    data = fetch_json(url)["data"]

    if arr_key is None:
        # No array: whole data object is the single "record"
        df = pd.json_normalize(data)
        print(f"{len(df)} record(s)")
        return df

    records = data.get(arr_key, [])
    df = pd.json_normalize(records)
    print(f"{len(df)} record(s)")
    return df if not df.empty else None


def save_raw_json(**payloads) -> None:
    """Keep structured feeds (geofencing GeoJSON) as their raw JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for name, payload in payloads.items():
        path = join(DATA_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"[save] {name}.json ({len(payload.get('data', {}))} records)")


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    for feed_name, arr_key in FEEDS.items():
        try:
            df = feed_to_df(feed_name, arr_key)
            if df is not None:
                out = join(DATA_DIR, f"{feed_name}.csv")
                df.to_csv(out, index=False)
                print(f"[save] {feed_name}.csv -> {out}")
        except Exception as e:  # noqa: BLE001 - keep going, report per-feed
            print(f"\n[!] {feed_name}.json FAILED: {e}")

    # Structured feed: keep as raw JSON (GeoJSON doesn't flatten well).
    try:
        save_raw_json(
            geofencing_zones=fetch_json(f"{GBFS_BASE}/geofencing_zones.json")
        )
    except Exception as e:  # noqa: BLE001
        print(f"[!] geofencing_zones.json FAILED: {e}")

    # Combined demo snapshot: live availability + station names/coords merged
    # into one analysis-ready file (station_id normalised to str to avoid the
    # int-vs-str merge trap).
    try:
        status = feed_to_df("station_status", "stations")
        info = feed_to_df("station_information", "stations")
        if status is not None and info is not None:
            keep_info = ["station_id", "name", "lat", "lon", "capacity"]
            info = info[info.columns.intersection(keep_info)].copy()
            status["station_id"] = status["station_id"].astype(str)
            info["station_id"] = info["station_id"].astype(str)
            demo = status.merge(info, on="station_id", how="left")
            demo_path = join(DATA_DIR, "DEMO_DATA.csv")
            demo.to_csv(demo_path, index=False)
            print(
                f"[save] DEMO_DATA.csv -> {demo_path} "
                f"({len(demo)} stations, {len(demo.columns)} cols)"
            )
    except Exception as e:  # noqa: BLE001
        print(f"[!] DEMO_DATA.csv FAILED: {e}")

    print("\nDone. CSVs written to:", DATA_DIR)


if __name__ == "__main__":
    main()