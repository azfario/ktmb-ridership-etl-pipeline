"""PostgreSQL connection setup for the KTMB pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_engine() -> Engine:
    """Create a PostgreSQL engine from environment settings."""
    load_dotenv(PROJECT_ROOT / ".env")

    required = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing database settings: {', '.join(missing)}")

    try:
        port = int(os.environ["DB_PORT"])
    except ValueError as error:
        raise ValueError("DB_PORT must be a whole number.") from error

    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=port,
        database=os.environ["DB_NAME"],
    )
    return create_engine(url)


if __name__ == "__main__":
    engine = get_engine()

    with engine.connect() as connection:
        user, database = connection.execute(
            text("SELECT current_user, current_database()")
        ).one()
        table = connection.execute(
            text("SELECT to_regclass('public.ktmb_ridership')")
        ).scalar_one()

    engine.dispose()

    if table is None:
        raise RuntimeError("The ktmb_ridership table was not found.")

    print(f"Connected as {user} to {database}.")
    print(f"Found table: {table}")
