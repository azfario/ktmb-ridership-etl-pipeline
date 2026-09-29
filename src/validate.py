from pathlib import Path

import pandas as pd
from datetime import date

REQUIRED_COLUMNS = ("date", "service", "ridership")

EXPECTED_SERVICES = {
    "komuter",
    "komuter_utara",
    "intercity",
    "ets",
    "shuttle_tebrau",
}


def validate_ktmb_data(data: pd.DataFrame) -> None:
    """Raise a clear error if the KTMB data fails a required check."""
    if data.empty:
        raise ValueError("The KTMB dataset has no rows.")

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    for column in REQUIRED_COLUMNS:
        missing_count = int(data[column].isna().sum())
        if missing_count:
            raise ValueError(f"{column} has {missing_count} missing value(s).")

    dates = pd.to_datetime(
        data["date"], format="%Y-%m-%d", errors="coerce"
    )
    if dates.isna().any():
        raise ValueError("date contains invalid values; expected YYYY-MM-DD.")

    invalid_services = ~data["service"].isin(EXPECTED_SERVICES)
    if invalid_services.any():
        examples = (
            data.loc[invalid_services, "service"]
            .astype(str)
            .unique()
            .tolist()[:5]
        )
        raise ValueError(f"Unexpected service value(s): {examples}")

    ridership = pd.to_numeric(data["ridership"], errors="coerce")
    if ridership.isna().any():
        raise ValueError("ridership contains non-numeric values.")

    if (ridership < 0).any():
        raise ValueError("ridership contains negative values.")

    if (ridership % 1 != 0).any():
        raise ValueError("ridership must contain whole numbers.")

def validate_processed_data(data: pd.DataFrame) -> date:
    """Check cleaned rows and return the latest dataset date."""
    validate_ktmb_data(data)

    duplicate_keys = data.duplicated(
        subset=["date", "service"], keep=False
    )
    if duplicate_keys.any():
        duplicate_count = int(duplicate_keys.sum())
        raise ValueError(
            "Processed data has "
            f"{duplicate_count} row(s) with duplicate date/service keys."
        )

    latest_date = pd.to_datetime(
        data["date"], format="%Y-%m-%d"
    ).max().date()

    if latest_date > date.today():
        raise ValueError(
            f"Latest dataset date {latest_date} is in the future."
        )

    return latest_date

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    raw_files = sorted(
        (project_root / "data" / "raw").glob("ktmb_ridership_*.csv")
    )
    if not raw_files:
        raise FileNotFoundError("No KTMB CSV found in data/raw.")

    raw_file = raw_files[-1]
    data = pd.read_csv(raw_file)
    validate_ktmb_data(data)
    print(f"Validation passed: {len(data)} rows in {raw_file.name}.")