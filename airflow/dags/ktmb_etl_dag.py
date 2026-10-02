from datetime import date, timedelta

import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="ktmb_ridership_daily",
    schedule="0 6 * * *",
    start_date=pendulum.datetime(
        2026, 9, 30, tz="Asia/Kuala_Lumpur"
    ),
    catchup=False,
    max_active_runs=1,
    tags=["ktmb", "etl"],
)
def ktmb_etl_dag():
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def extract_ktmb() -> str:
        from extract import RAW_DIR, extract_ktmb_data

        data = extract_ktmb_data()
        raw_path = RAW_DIR / f"ktmb_ridership_{date.today().isoformat()}.csv"

        if not raw_path.exists():
            raise FileNotFoundError(raw_path)

        print(f"Downloaded {len(data)} rows to {raw_path}")
        return str(raw_path)

    @task
    def validate_raw(raw_path: str) -> str:
        import pandas as pd
        from validate import validate_ktmb_data

        data = pd.read_csv(raw_path)
        validate_ktmb_data(data)

        print(f"Raw validation passed: {len(data)} rows")
        return raw_path

    @task
    def transform_ktmb(raw_path: str) -> str:
        import pandas as pd
        from transform import save_processed_data, transform_ktmb_data
        from validate import validate_processed_data

        raw_data = pd.read_csv(raw_path)
        processed_data = transform_ktmb_data(raw_data)
        latest_date = validate_processed_data(processed_data)
        processed_path = save_processed_data(processed_data)

        print(
            f"Transformed {len(processed_data)} rows; "
            f"latest date: {latest_date}"
        )
        return str(processed_path)

    @task
    def load_postgres(processed_path: str) -> str:
        import pandas as pd
        from load import load_ktmb_data

        processed_data = pd.read_csv(processed_path)
        before, after = load_ktmb_data(processed_data)

        print(f"PostgreSQL rows: {before} -> {after}")
        return processed_path

    @task
    def validate_load(processed_path: str) -> None:
        import pandas as pd
        from sqlalchemy import text

        from database import get_engine
        from validate import validate_processed_data

        processed_data = pd.read_csv(processed_path)
        latest_source_date = validate_processed_data(processed_data)

        engine = get_engine()
        try:
            with engine.connect() as connection:
                row_count, latest_database_date = connection.execute(
                    text(
                        "SELECT COUNT(*), MAX(date) "
                        "FROM ktmb_ridership"
                    )
                ).one()
        finally:
            engine.dispose()

        if row_count < len(processed_data):
            raise ValueError(
                f"Database has {row_count} rows; "
                f"processed file has {len(processed_data)}."
            )

        if latest_database_date != latest_source_date:
            raise ValueError(
                f"Database latest date {latest_database_date} "
                f"does not match source date {latest_source_date}."
            )

        print(
            f"Load validation passed: {row_count} database rows; "
            f"latest date: {latest_database_date}"
        )

    raw_path = extract_ktmb()
    checked_raw_path = validate_raw(raw_path)
    processed_path = transform_ktmb(checked_raw_path)
    loaded_path = load_postgres(processed_path)
    validate_load(loaded_path)


ktmb_etl_dag()