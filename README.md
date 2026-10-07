# Malaysia KTMB Ridership ETL Pipeline

A Python pipeline that downloads official KTMB ridership data, cleans it, and loads it into PostgreSQL for SQL analysis.

**Tools:** Python, Pandas, requests, PostgreSQL, SQLAlchemy, psycopg, Docker, Apache Airflow, and pytest.

**Source:** [data.gov.my KTMB daily ridership CSV](https://storage.data.gov.my/transportation/ktmb/ridership_ktmb_daily.csv).

## How it works

```text
Official CSV -> Raw data -> Validate and clean -> PostgreSQL -> SQL analytics
```

- Checks required fields, valid dates, service names, and nonnegative whole-number ridership.
- Adds calendar columns and handles duplicates.
- Downloads the full CSV each run, then inserts new records and updates changed records without creating duplicate date/service keys.
- Airflow schedules the pipeline daily at **06:00 Malaysia time**.
- SQL provides daily/monthly totals, moving averages, service shares, and weekday/weekend comparisons.

## Data preview: raw to final

Examples below come from the saved **6 October 2026** snapshot. Values will change as the source is updated.

### 1. Raw data

The original CSV is saved in `data/raw/`. Each row contains one service's ridership for one date.

| date | service | ridership |
|---|---|---:|
| 2020-10-15 | ets | 737 |
| 2020-10-15 | intercity | 807 |
| 2020-10-15 | komuter_utara | 3,776 |

### 2. Cleaned data and PostgreSQL

Dates and ridership are converted to the correct types, duplicates are checked, and calendar columns are added. The cleaned CSV is saved in `data/processed/` and loaded into the PostgreSQL table `ktmb_ridership`.

| date | service | ridership | day_of_week | month | year | is_weekend |
|---|---|---:|---|---|---:|---|
| 2020-10-15 | ets | 737 | Thursday | October | 2020 | False |
| 2020-10-15 | intercity | 807 | Thursday | October | 2020 | False |
| 2020-10-15 | komuter_utara | 3,776 | Thursday | October | 2020 | False |

### 3. Final daily summary

The SQL view `mart_daily_ridership` combines the service rows into one daily total.

| date | total_ridership | service_count |
|---|---:|---:|
| 2020-10-15 | 5,320 | 3 |

For this date, **737 + 807 + 3,776 = 5,320**. Only three services are reported in this early example; later dates include five. Comparison queries use matching service coverage, and monthly percentage changes require complete months.

## Run the project

Use standalone **PowerShell** from the project folder, with **Docker Desktop running**.

First, create `.env` from the example if it does not already exist, then set your database password:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Start PostgreSQL and run the pipeline:

```powershell
docker compose up -d db
docker compose run --rm --build etl
```

Create the analytics views and display their results:

```powershell
Get-Content .\sql\analytics.sql -Raw |
    docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -P pager=off -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Start Airflow:

```powershell
docker compose up -d --build airflow
```

Open [localhost:8081](http://localhost:8081), enable `ktmb_ridership_daily`, and trigger a run. To retrieve the generated login details:

```powershell
docker compose exec -T airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

The Docker database is available to Windows apps at **localhost:5433**. Keep the PC and Docker running for scheduled jobs. Pipeline logs are saved in `logs/pipeline.log`; Airflow task logs are available in its interface.

## Tests

With Python 3.13 installed:

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r .\requirements-dev.txt
& ".\.venv\Scripts\python.exe" -m pytest .\tests -v
```

**28 tests passed**, covering validation, transformation, dates, duplicates, calendar columns, and CSV output using sample data.

## Project files and next step

- [`src/`](src/) — Python pipeline.
- [`sql/analytics.sql`](sql/analytics.sql) — analytics views and queries.
- [`airflow/dags/ktmb_etl_dag.py`](airflow/dags/ktmb_etl_dag.py) — daily workflow.
- [`tests/`](tests/) — automated tests.

Credentials, generated CSVs, logs, caches, and Power BI drafts are excluded from Git.

**Power BI is postponed until the final project phase.**

