# Malaysia KTMB Ridership ETL Pipeline

Extracts official KTMB ridership data, cleans it, and loads it into PostgreSQL for analysis.

**Data source:** [data.gov.my daily KTMB ridership CSV](https://storage.data.gov.my/transportation/ktmb/ridership_ktmb_daily.csv).

## Tech Stack

- Python 3.13
- Pandas and requests
- PostgreSQL 18 via Docker
- SQLAlchemy and psycopg
- python-dotenv
- Apache Airflow 3.3.2
- pytest

---

## Setup

Use standalone **PowerShell** with Docker Desktop running.

**1. Clone the repository**

```powershell
git clone https://github.com/azfario/ktmb-ridership-etl-pipeline.git
cd ktmb-ridership-etl-pipeline
```

**2. Create a virtual environment**

```powershell
python -m venv .venv
```

**3. Install dependencies**

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r .\requirements-dev.txt
```

**4. Configure environment variables**

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Set `DB_PASSWORD` to your database password and `DB_PORT` to **5433** for the local Python connection. Keep `DB_HOST=localhost`, `DB_NAME=ktmb_ridership`, and `DB_USER=ktmb_app`.

**5. Start PostgreSQL**

```powershell
docker compose up -d db
docker compose ps
```

Wait until the database shows **healthy**.

**6. Ensure the table exists**

```powershell
Get-Content .\sql\create_tables.sql -Raw |
    docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

The table is also created automatically when a new database volume is initialized.

**7. Run the pipeline**

```powershell
& ".\.venv\Scripts\python.exe" .\src\main.py
```

**8. Create the analytics views**

```powershell
Get-Content .\sql\analytics.sql -Raw |
    docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -P pager=off -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

**9. Start Airflow**

```powershell
docker compose up -d --build airflow
```

Open [localhost:8081](http://localhost:8081), enable `ktmb_ridership_daily`, and trigger a run. Retrieve the generated login details with:

```powershell
docker compose exec -T airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

---

## Database Schema

Table: `ktmb_ridership`

| Column | Type | Description |
|---|---|---|
| date | DATE | Reporting date |
| service | VARCHAR(50) | KTMB service identifier |
| ridership | INTEGER | Nonnegative reported ridership |
| day_of_week | VARCHAR(9) | Day name |
| month | VARCHAR(9) | Month name |
| year | INTEGER | Reporting year |
| is_weekend | BOOLEAN | True for Saturday and Sunday |

All columns are required. The primary key is **(date, service)**.

---

## Data Preview

Examples from the saved **6 October 2026** snapshot.

**Raw data** — the original CSV is saved in `data/raw/`.

| date | service | ridership |
|---|---|---:|
| 2020-10-15 | ets | 737 |
| 2020-10-15 | intercity | 807 |
| 2020-10-15 | komuter_utara | 3,776 |

**Cleaned data** — types are converted, duplicates are checked, and calendar columns are added. These records are saved in `data/processed/` and loaded into PostgreSQL.

| date | service | ridership | day_of_week | month | year | is_weekend |
|---|---|---:|---|---|---:|---|
| 2020-10-15 | ets | 737 | Thursday | October | 2020 | False |
| 2020-10-15 | intercity | 807 | Thursday | October | 2020 | False |
| 2020-10-15 | komuter_utara | 3,776 | Thursday | October | 2020 | False |

**Final daily summary** — `mart_daily_ridership` combines the service rows into one daily total.

| date | total_ridership | service_count |
|---|---:|---:|
| 2020-10-15 | 5,320 | 3 |

Here, **737 + 807 + 3,776 = 5,320**. This early date has three reported services; later dates include five.

---

## Features

- Downloads the official KTMB CSV and preserves a raw copy.
- Validates dates, service names, required values, and ridership.
- Loads PostgreSQL with duplicate-safe inserts and updates.
- Schedules daily runs at **06:00 Malaysia time** using Airflow.
- Provides daily/monthly totals, moving averages, service shares, and weekday/weekend comparisons.
- Writes pipeline logs to `logs/pipeline.log` and provides Airflow task logs.
- Includes **28 passing validation and transformation tests**.

---

## Design Decisions

- **Idempotency** — the `(date, service)` key and UPSERT logic allow repeated loads without duplicate records.
- **Full-source extraction** — each run processes the full CSV, then inserts new records and updates changed values.
- **Environment variables** — database credentials are configured through `.env`, which is ignored by Git.
- **Service coverage** — comparison queries use dates with all five services; monthly changes require consecutive complete months.
- **Reusable functions** — the local pipeline and Airflow tasks call the same ETL functions.

---

## Tests

```powershell
& ".\.venv\Scripts\python.exe" -m pytest .\tests -v
```

The tests use small sample datasets and temporary CSV output.

**Next step:** Complete the Power BI dashboard in the final project phase.

