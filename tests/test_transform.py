import pandas as pd
import pytest

from src import transform
from src.transform import save_processed_data, transform_ktmb_data


def test_converts_dates_and_numeric_strings():
    data = pd.DataFrame(
        {
            "date": ["2024-01-08", "2024-01-05"],
            "service": ["ets", "ets"],
            "ridership": ["200", "100"],
        }
    )

    result = transform_ktmb_data(data)

    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert pd.api.types.is_integer_dtype(result["ridership"])
    assert result["date"].tolist() == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-01-08"),
    ]
    assert result["ridership"].tolist() == [100, 200]


@pytest.mark.parametrize(
    "date_text, day_name, month_name, year, is_weekend",
    [
        ("2023-12-31", "Sunday", "December", 2023, True),
        ("2024-01-01", "Monday", "January", 2024, False),
        ("2024-01-05", "Friday", "January", 2024, False),
        ("2024-01-06", "Saturday", "January", 2024, True),
    ],
)
def test_adds_calendar_columns(
    date_text, day_name, month_name, year, is_weekend
):
    data = pd.DataFrame(
        [{"date": date_text, "service": "ets", "ridership": 100}]
    )

    result = transform_ktmb_data(data)
    row = result.iloc[0]

    assert row["day_of_week"] == day_name
    assert row["month"] == month_name
    assert row["year"] == year
    assert row["is_weekend"] == is_weekend
    assert pd.api.types.is_bool_dtype(result["is_weekend"])


def test_sorts_by_date_then_service_and_resets_index():
    data = pd.DataFrame(
        [
            {"date": "2024-01-06", "service": "intercity", "ridership": 10},
            {"date": "2024-01-05", "service": "komuter", "ridership": 20},
            {"date": "2024-01-05", "service": "ets", "ridership": 30},
        ],
        index=[9, 2, 7],
    )

    result = transform_ktmb_data(data)

    assert list(zip(result["date"], result["service"])) == [
        (pd.Timestamp("2024-01-05"), "ets"),
        (pd.Timestamp("2024-01-05"), "komuter"),
        (pd.Timestamp("2024-01-06"), "intercity"),
    ]
    assert result["ridership"].tolist() == [30, 20, 10]
    assert result.index.tolist() == [0, 1, 2]


def test_removes_exact_duplicates():
    data = pd.DataFrame(
        [
            {"date": "2024-01-05", "service": "ets", "ridership": 100},
            {"date": "2024-01-05", "service": "ets", "ridership": 100},
            {"date": "2024-01-06", "service": "ets", "ridership": 200},
        ]
    )

    result = transform_ktmb_data(data)

    assert len(result) == 2
    assert result["date"].tolist() == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-01-06"),
    ]
    assert result["ridership"].tolist() == [100, 200]


def test_rejects_conflicting_date_service_rows():
    data = pd.DataFrame(
        [
            {"date": "2024-01-05", "service": "ets", "ridership": 100},
            {"date": "2024-01-05", "service": "ets", "ridership": 101},
        ]
    )

    with pytest.raises(ValueError, match="Conflicting rows"):
        transform_ktmb_data(data)


def test_retains_different_services_on_same_date():
    data = pd.DataFrame(
        [
            {"date": "2024-01-05", "service": "ets", "ridership": 100},
            {"date": "2024-01-05", "service": "intercity", "ridership": 200},
        ]
    )

    result = transform_ktmb_data(data)

    assert len(result) == 2
    assert result["service"].tolist() == ["ets", "intercity"]
    assert result["ridership"].tolist() == [100, 200]


def test_does_not_modify_input():
    data = pd.DataFrame(
        {
            "date": ["2024-01-06", "2024-01-05"],
            "service": ["ets", "ets"],
            "ridership": ["200", "100"],
        },
        index=[7, 3],
    )
    original = data.copy(deep=True)

    transform_ktmb_data(data)

    pd.testing.assert_frame_equal(data, original)


def test_saves_processed_csv(tmp_path, monkeypatch):
    output_dir = tmp_path / "nested" / "processed"
    monkeypatch.setattr(transform, "PROCESSED_DIR", output_dir)
    record = {
        "date": "2024-01-06",
        "service": "ets",
        "ridership": 123,
        "day_of_week": "Saturday",
        "month": "January",
        "year": 2024,
        "is_weekend": True,
    }
    expected = pd.DataFrame([record])
    data = pd.DataFrame([{**record, "date": pd.Timestamp("2024-01-06")}])

    output_path = save_processed_data(data)

    assert output_path == output_dir / "ktmb_ridership_clean.csv"
    pd.testing.assert_frame_equal(pd.read_csv(output_path), expected)
