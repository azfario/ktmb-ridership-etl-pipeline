from pathlib import Path

import pandas as pd
from sqlalchemy import text

from database import get_engine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
BATCH_SIZE = 500

UPSERT_SQL = text(
    """
    INSERT INTO ktmb_ridership (
        date, service, ridership, day_of_week, month, year, is_weekend
    )
    VALUES (
        :date, :service, :ridership, :day_of_week, :month, :year, :is_weekend
    )
    ON CONFLICT (date, service) DO UPDATE SET
        ridership = EXCLUDED.ridership,
        day_of_week = EXCLUDED.day_of_week,
        month = EXCLUDED.month,
        year = EXCLUDED.year,
        is_weekend = EXCLUDED.is_weekend
    WHERE ktmb_ridership.ridership IS DISTINCT FROM EXCLUDED.ridership
       OR ktmb_ridership.day_of_week IS DISTINCT FROM EXCLUDED.day_of_week
       OR ktmb_ridership.month IS DISTINCT FROM EXCLUDED.month
       OR ktmb_ridership.year IS DISTINCT FROM EXCLUDED.year
       OR ktmb_ridership.is_weekend IS DISTINCT FROM EXCLUDED.is_weekend
    """
)


def load_ktmb_data(data: pd.DataFrame) -> tuple[int, int]:
    """Insert new rows and update changed rows in PostgreSQL."""
    required = {
        "date",
        "service",
        "ridership",
        "day_of_week",
        "month",
        "year",
        "is_weekend",
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing columns for database load: {missing}")

    if data.empty:
        raise ValueError("There are no rows to load.")

    if data.duplicated(["date", "service"]).any():
        raise ValueError("Duplicate date and service pairs cannot be loaded.")

    records = []
    for row in data.itertuples(index=False):
        records.append(
            {
                "date": pd.Timestamp(row.date).date(),
                "service": str(row.service),
                "ridership": int(row.ridership),
                "day_of_week": str(row.day_of_week),
                "month": str(row.month),
                "year": int(row.year),
                "is_weekend": bool(row.is_weekend),
            }
        )

    engine = get_engine()
    try:
        with engine.begin() as connection:
            before = connection.execute(
                text("SELECT COUNT(*) FROM ktmb_ridership")
            ).scalar_one()

            for start in range(0, len(records), BATCH_SIZE):
                batch = records[start : start + BATCH_SIZE]
                connection.execute(UPSERT_SQL, batch)

            after = connection.execute(
                text("SELECT COUNT(*) FROM ktmb_ridership")
            ).scalar_one()

            if after < before:
                raise ValueError(
                    f"Database row count fell from {before} to {after}."
                )

            if after < len(records):
                raise ValueError(
                    f"Database has {after} rows after loading "
                    f"{len(records)} distinct source rows."
                )

            latest_source_date = max(record["date"] for record in records)
            latest_database_date = connection.execute(
                text("SELECT MAX(date) FROM ktmb_ridership")
            ).scalar_one()

            if latest_database_date != latest_source_date:
                raise ValueError(
                    f"Latest database date {latest_database_date} "
                    f"does not match latest source date {latest_source_date}."
                )

            stored_rows = connection.execute(
                text(
                    """
                    SELECT date, service, ridership, day_of_week,
                           month, year, is_weekend
                    FROM ktmb_ridership
                    """
                )
            ).mappings()

            stored_by_key = {
                (row["date"], row["service"]): row
                for row in stored_rows
            }

            columns_to_check = (
                "ridership",
                "day_of_week",
                "month",
                "year",
                "is_weekend",
            )

            for record in records:
                key = (record["date"], record["service"])
                stored = stored_by_key.get(key)

                if stored is None:
                    raise ValueError(
                        f"Database is missing date {key[0]}, "
                        f"service {key[1]}."
                    )

                for column in columns_to_check:
                    if stored[column] != record[column]:
                        raise ValueError(
                            f"Database mismatch for date {key[0]}, "
                            f"service {key[1]}, column {column}: "
                            f"expected {record[column]!r}, "
                            f"found {stored[column]!r}."
                        )

        return before, after
    finally:
        engine.dispose()


if __name__ == "__main__":
    from transform import transform_ktmb_data
    from validate import validate_ktmb_data, validate_processed_data

    raw_files = sorted(RAW_DIR.glob("ktmb_ridership_*.csv"))
    if not raw_files:
        raise FileNotFoundError("No KTMB CSV found in data/raw.")

    raw_data = pd.read_csv(raw_files[-1])
    validate_ktmb_data(raw_data)

    processed_data = transform_ktmb_data(raw_data)
    validate_processed_data(processed_data)

    before, after = load_ktmb_data(processed_data)
    print(f"Input rows: {len(processed_data)}")
    print(f"Database rows: {before} -> {after}")
