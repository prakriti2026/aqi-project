import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load your API key from .env file
load_dotenv()
API_KEY = os.getenv("OPENAQ_API_KEY", "4b97e95a5bc952c448c02d7488a07f966b734a8e31723d9c6d29c628a095260d")

# Kathmandu coordinates
LAT = 27.7172
LON = 85.3240
RADIUS = 25000

# Where to save the data
DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_locations():
    print("Looking for sensors near Kathmandu...")
    url = "https://api.openaq.org/v3/locations"
    params = {
        "coordinates": f"{LAT},{LON}",
        "radius": RADIUS,
        "limit": 20,
    }
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    results = response.json().get("results", [])
    print(f"Found {len(results)} sensor locations!")
    return results

def fetch_measurements(location_id):
    """Get recent measurements using the sensors endpoint."""
    url = f"https://api.openaq.org/v3/locations/{location_id}/sensors"
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    sensors = response.json().get("results", [])
    rows = []

    for sensor in sensors:
        # Get the latest reading from each sensor
        latest = sensor.get("latest", {})
        coverage = sensor.get("coverage", {})
        parameter = sensor.get("parameter", {})

        if latest and latest.get("value") is not None:
            rows.append({
                "datetime": latest.get("datetime", {}).get("utc"),
                "parameter": parameter.get("name"),
                "value": latest.get("value"),
                "unit": parameter.get("units"),
                "location_id": location_id,
            })

    return rows

def main():
    locations = fetch_locations()

    if not locations:
        print("No sensors found. Check your API key or internet connection.")
        return

    all_rows = []
    for loc in locations:
        loc_id = loc["id"]
        loc_name = loc.get("name", "Unknown")
        print(f"  Fetching data from: {loc_name} (ID: {loc_id})")

        measurements = fetch_measurements(loc_id)

        for m in measurements:
            m["location"] = loc_name
            m["latitude"] = loc.get("coordinates", {}).get("latitude")
            m["longitude"] = loc.get("coordinates", {}).get("longitude")
            all_rows.append(m)

    if not all_rows:
        print("No measurements found.")
        return

    df = pd.DataFrame(all_rows)
    df = df[df["value"] >= 0]
    filename = f"kathmandu_aqi_{datetime.now().strftime('%Y%m%d')}.csv"
    save_path = DATA_DIR / filename
    df.to_csv(save_path, index=False)

    print(f"\nSuccess! Saved {len(df)} rows to {save_path}")
    print(f"\nParameters found: {df['parameter'].unique()}")
    print(f"\nFirst few rows:")
    print(df.head(10))

if __name__ == "__main__":
    main()