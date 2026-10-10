"""
Scheduled collector for the Brighton Bikeshare dashboard.

Runs the ETL pipeline once and appends a snapshot to data/history.csv.
Designed to be invoked by an OS scheduler (cron / Windows Task Scheduler /
GitHub Actions / etc.) every 5 minutes, independent of page views, so history
accumulates continuously.

Usage:
    python collect.py            # run one snapshot, print a short summary
    python collect.py --quiet    # run one snapshot, no console output

Exit code is 0 on success, 1 if the ETL failed.
"""

import argparse
import logging
import sys
from os.path import dirname, abspath

# Ensure we can import app.py regardless of the directory we're launched from.
sys.path.insert(0, dirname(abspath(__file__)))

from app import load, run_etl  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("collect")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quiet", action="store_true", help="suppress console output"
    )
    args = parser.parse_args()

    df, snapshot_time, error = run_etl()

    if error is not None or df is None:
        log.error("ETL failed: %s", error or "no dataframe returned")
        return 1

    if args.quiet:
        return 0

    log.info(
        "Snapshot %s: %d stations, %d bikes, %d docks "
        "(appended to history.csv)",
        snapshot_time,
        len(df),
        int(df["num_bikes_available"].sum()),
        int(df["num_docks_available"].sum()),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())