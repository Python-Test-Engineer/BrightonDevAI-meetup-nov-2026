# Brighton Bikeshare Web App — EXPLAINER

A small Flask web app that pulls **live Brighton cycle-hire data** (run by **Beryl**), runs an
**ETL pipeline**, and presents **data analysis** in the browser. It is built as a demo/teaching
project for the Brighton Web Dev Meetup — deliberately small, everything in plain Python +
pandas + a little HTML.

---

## 1. What it does

### The data source
Beryl publishes a public **GBFS** feed (General Bikeshare Feed Specification — a standard JSON
format used by bike-share systems worldwide). The live availability feed is:

```
https://beryl-gbfs-production.web.app/v2_2/Brighton/station_status.json
```

Every ~120 seconds Beryl refreshes this with the current state of all ~119 Brighton stations:
how many bikes are docked, how many free docks, whether the station is renting/returning, and
the last time it reported.

### The pipeline (ETL)
Each time you load the page, the app:

- **EXTRACT** — fetches two feeds:
  - `station_status.json`   → live bikes/docks per station
  - `station_information.json` → station names, lat/lon, dock capacity
- **TRANSFORM** — merges the two on `station_id`, converts types, derives a per-station
  utilisation % (share of capacity currently holding a bike).
- **LOAD** — appends a timestamped snapshot (one row per station) to `data/history.csv`, so
  you accumulate a time series you can analyse later.
- **ANALYSE** — computes summary stats and renders them in the dashboard.

### The dashboard
The browser page (`templates/index.html`) shows:

- **Summary cards** — total stations, total bikes available, total free docks, and overall
  network utilisation %.
- **Top stations** — which stations currently have the most bikes, and the most free docks.
- **Change vs. last snapshot** — which stations gained/lost the most bikes since the previous
  page load (once enough history exists).
- **Full station table** — every station with bike/dock counts, utilisation colour-coded
  (green = healthy, amber = low, red = empty or near-full).

---

## 2. The files

| File | Purpose |
|------|---------|
| `app.py` | Flask app: ETL pipeline + analysis + routes |
| `templates/index.html` | The dashboard template (HTML + inline CSS) |
| `collect.py` | Standalone collector: runs ETL once, appends a snapshot (for scheduled use) |
| `data.py` | Fetch data from any/most of the 9 Beryl GBFS feeds and save as CSV(s) |
| `data/` | Output folder (history.csv, per-feed CSVs, DEMO_DATA.csv) — gitignored |

---

## 3. How to use it

### Run the dashboard
```bash
cd "C:\Users\mrcra\Desktop\brighton-web-dev-meetup-nov-2026\web_app"
python app.py
```
Open **http://127.0.0.1:5000** in a browser. Each page refresh re-runs the ETL and appends a
snapshot to history. Stop the server with **Ctrl+C**.

### Collect data on a schedule (recommended)
History grows fast if you poll every few minutes, and you don't need the page open:

```bash
python collect.py            # fetch + append one snapshot, print a summary
python collect.py --quiet    # same, no console output
```

To schedule it every 5 minutes on Windows (replace the python path with `where python`):
```
schtasks /Create /TN "BrightonBikeshareCollect" /SC MINUTE /MO 5 /TR "\"C:\path\to\python.exe\" \"...\web_app\collect.py\""
```

### Pull the raw feeds to CSV
```bash
python data.py
```
Writes one CSV per feed into `data/` (station_information.csv, station_status.csv,
free_bike_status.csv, vehicle_types.csv, system_pricing_plans.csv, system_regions.csv,
gbfs_versions.csv, system_information.csv) plus a combined `data/DEMO_DATA.csv` (live
availability merged with station names/coords) and `geofencing_zones.json` (kept as raw JSON
since GeoJSON doesn't flatten to a table). A full per-feed explainer is the comment at the top
of `data.py`.

### Requirements
- Python 3 + `flask`, `pandas`, `requests` (all installed in this project's environment).

---

## 4. What you can do with the captured data

Once `history.csv`/`DEMO_DATA.csv` accumulates snapshots over time, you can:

- Track **empty / full stations over time** to spot where riders get locked out.
- Measure **arrivals vs. departures** per station by comparing consecutive snapshots.
- Build **forecasts** (a plan is written up in `REPORT.md` at the project root) — e.g. predict
  which stations will be empty/full in the next 30–60 minutes using a "baseline = current"
  model first, then move to time-of-day profiles and lightweight ML once history is thick.

---

## 5. Notes & pitfalls we hit

- **`station_id` type mismatch** — `station_status` returns it as a number, other feeds as a
  string. Merge after casting both to `str` (a silent killer in pandas merges).
- **`free_bike_status` is NOT empty** — it carries ~862 free-ranging bikes/e-bikes/scooters;
  don't skip it if you care about the full fleet, not just docked bikes.
- **`geofencing_zones` is GeoJSON** — don't try to flatten it to CSV; keep the raw JSON.
- **Debug recon** — find all available feeds from the manifest:
  `https://beryl-gbfs-production.web.app/v2_2/Brighton/gbfs.json`.

---

## 6. Quick demo flow

1. `python app.py` → open http://127.0.0.1:5000 → see live stats.
2. Refresh a few times → history accumulates → the "change vs last snapshot" section appears.
3. `python data.py` → inspect `data/DEMO_DATA.csv` in Excel/pandas.
4. Let `collect.py` run on schedule → build the time series → try forecasting (see REPORT.md).