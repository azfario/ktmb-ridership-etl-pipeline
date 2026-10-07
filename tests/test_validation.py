from datetime import date, timedelta

import pandas as pd
import pytest

from src.validate import (
    validate_ktmb_data,
    validate_processed_data,
)


def make_data(**changes):
    """Create one sample row, optionally replacing some values."""
    row = {
        "date": "2024-01-15",
        "service": "ets",
        "ridership": 100,
    }
    row.update(changes)
    return pd.DataFrame([row])


@pytest.mark.parametrize("ridership", [0, 100])
def test_accepts_valid_ridership(ridership):
    data = make_data(ridership=ridership)

    assert validate_ktmb_data(data) is None


@pytest.mark.parametrize(
    "changes, error_message",
    [
        ({"ridership": -1}, "negative"),
        ({"ridership": 10.5}, "whole numbers"),
        ({"ridership": "abc"}, "non-numeric"),
        ({"service": "unknown"}, "Unexpected service"),
        ({"date": "2024-02-30"}, "invalid"),
        ({"date": None}, "missing"),
        ({"service": None}, "missing"),
        ({"ridership": None}, "missing"),
    ],
)
def test_rejects_invalid_values(changes, error_message):
    data = make_data(**changes)

    with pytest.raises(ValueError, match=error_message):
        validate_ktmb_data(data)


def test_rejects_empty_data():
    data = pd.DataFrame(columns=["date", "service", "ridership"])

    with pytest.raises(ValueError, match="no rows"):
        validate_ktmb_data(data)


@pytest.mark.parametrize("column", ["date", "service", "ridership"])
def test_rejects_missing_columns(column):
    data = make_data().drop(columns=[column])

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_ktmb_data(data)


def test_processed_data_rejects_duplicate_keys():
    data = pd.concat([make_data(), make_data()], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate"):
        validate_processed_data(data)


def test_processed_data_rejects_future_dates():
    tomorrow = date.today() + timedelta(days=1)
    data = make_data(date=tomorrow.isoformat())

    with pytest.raises(ValueError, match="future"):
        validate_processed_data(data)


def test_processed_data_returns_latest_date():
    data = pd.concat(
        [
            make_data(date="2024-01-20"),
            make_data(date="2024-01-10"),
        ],
        ignore_index=True,
    )

    assert validate_processed_data(data) == date(2024, 1, 20)
