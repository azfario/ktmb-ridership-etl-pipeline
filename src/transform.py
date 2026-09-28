from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def transform_ktmb_data(data: pd.DataFrame) -> pd.DataFrame:
    """Convert types, handle duplicates, and add calendar columns."""
    transformed = data.copy()

    transformed["date"] = pd.to_datetime(
        transformed["date"], format="%Y-%m-%d"
    )
    transformed["ridership"] = pd.to_numeric(
        transformed["ridership"]
    ).astype("int64")

    transformed = transformed.drop_duplicates().copy()

    conflicting_keys = transformed.duplicated(
        subset=["date", "service"], keep=False
    )
    if conflicting_keys.any():
        raise ValueError(
            "Conflicting rows found for the same date and service."
        )

    transformed["day_of_week"] = transformed["date"].dt.day_name()
    transformed["month"] = transformed["date"].dt.month_name()
    transformed["year"] = transformed["date"].dt.year
    transformed["is_weekend"] = transformed["date"].dt.dayofweek >= 5

    return transformed.sort_values(
        ["date", "service"]
    ).reset_index(drop=True)


def save_processed_data(data: pd.DataFrame) -> Path:
    """Save the transformed table as a CSV and return its path."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "ktmb_ridership_clean.csv"
    data.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return output_path


if __name__ == "__main__":
    from validate import validate_ktmb_data

    raw_files = sorted(RAW_DIR.glob("ktmb_ridership_*.csv"))
    if not raw_files:
        raise FileNotFoundError("No KTMB CSV found in data/raw.")

    raw_data = pd.read_csv(raw_files[-1])
    validate_ktmb_data(raw_data)

    processed_data = transform_ktmb_data(raw_data)
    validate_ktmb_data(processed_data)

    output_path = save_processed_data(processed_data)
    print(f"Processed {len(processed_data)} rows.")
    print(processed_data.head())
    print(f"Saved to {output_path}")