import os
from datetime import datetime

import pandas as pd
import requests

# Define endpoints
station_url = (
    "https://beryl-gbfs-production.web.app/v2_2/Brighton/station_status.json"
)


def fetch_live_bikeshare_data():
    try:
        print(f"[1/4] Requesting live data from {station_url} ...")
        response = requests.get(station_url, timeout=15)
        response.raise_for_status()
        print(f"[2/4] Request OK (status {response.status_code}), parsing JSON ...")

        data = response.json()

        # Extract stations list from the JSON tree
        stations_list = data["data"]["stations"]

        print(f"[3/4] Found {len(stations_list)} stations in payload.")

        # Flatten into a dataframe
        df = pd.DataFrame(stations_list)

        # Convert epoch timestamp to readable format
        df["last_reported"] = pd.to_datetime(df["last_reported"], unit="s")

        print(f"[4/4] Successfully loaded {len(df)} live station datasets!")
        return df

    except Exception as e:
        print(f"Error gathering dataset: {e}")
        return None


# Generate dataframe
btn_live_df = fetch_live_bikeshare_data()
if btn_live_df is not None:
    print(btn_live_df[["station_id", "num_bikes_available", "num_docks_available"]].head())

    # Save to a timestamped CSV in the same folder as this script
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, f"live_bikeshare_{timestamp}.csv")
    btn_live_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(btn_live_df)} rows to: {out_path}")
else:
    print("\nNo data retrieved; nothing to save.")
