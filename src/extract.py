from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests


CSV_URL = (
    "https://storage.data.gov.my/transportation/ktmb/"
    "ridership_ktmb_daily.csv"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def extract_ktmb_data() -> pd.DataFrame:
    """Download the official CSV, save its original bytes, and read it."""
    try:
        response = requests.get(CSV_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Could not download the KTMB CSV.") from error

    if not response.content:
        raise ValueError("The downloaded KTMB CSV is empty.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"ktmb_ridership_{date.today().isoformat()}.csv"
    raw_path.write_bytes(response.content)

    try:
        return pd.read_csv(BytesIO(response.content))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        raise ValueError(f"Could not read the CSV saved at {raw_path}.") from error


if __name__ == "__main__":
    data = extract_ktmb_data()
    print(f"Downloaded {len(data)} rows.")
    print(data.head())
    print("Original CSV saved in data/raw.")