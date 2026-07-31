import numpy as np
import pandas as pd
import pytest

from src.data.utils import get_skiprows, CreateFeatures


def make_raw_csv(tmp_path, blank_line_at=3):
    """Write a minimal CSV with a blank line at the given row index."""
    lines = []
    for i in range(blank_line_at):
        lines.append(f"header_row_{i}\n")
    lines.append("\n")  # blank line
    lines.append("col1,col2\n")
    lines.append("1,2\n")
    p = tmp_path / "test.csv"
    p.write_text("".join(lines))
    return str(p)


def make_weather_df():
    """Minimal DataFrame that CreateFeatures expects."""
    return pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=10),
        "Location": ["Sydney"] * 10,
        "MinTemp": np.random.uniform(10, 20, 10).astype("float32"),
        "MaxTemp": np.random.uniform(20, 35, 10).astype("float32"),
        "Rainfall": np.random.uniform(0, 5, 10).astype("float32"),
        "Evaporation": np.random.uniform(2, 8, 10).astype("float32"),
        "Sunshine": np.random.uniform(4, 10, 10).astype("float32"),
        "WindGustDir": ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N", "NE"],
        "WindGustSpeed": np.random.uniform(20, 60, 10).astype("float32"),
        "Humidity9am": pd.array([70, 65, 80, 75, 60, 55, 72, 68, 77, 63], dtype="Int16"),
        "Pressure9am": np.random.uniform(1010, 1025, 10).astype("float32"),
        "Temp9am": np.random.uniform(12, 22, 10).astype("float32"),
        "Humidity3pm": pd.array([50, 45, 60, 55, 40, 35, 52, 48, 57, 43], dtype="Int16"),
        "Cloud9am": np.random.uniform(0, 8, 10).astype("float32"),
        "Cloud3pm": np.random.uniform(0, 8, 10).astype("float32"),
        "WindDir9am": ["N"] * 10,
        "WindDir3pm": ["S"] * 10,
        "Temp3pm": np.random.uniform(18, 30, 10).astype("float32"),
        "Pressure3pm": np.random.uniform(1008, 1022, 10).astype("float32"),
        "WindSpeed9am": np.random.uniform(5, 30, 10).astype("float32"),
        "WindSpeed3pm": np.random.uniform(10, 40, 10).astype("float32"),
        "RainToday": ["No", "No", "Yes", "No", "No", "Yes", "No", "No", "No", "Yes"],
        "RainTomorrow": ["No", "Yes", "No", "No", "Yes", "No", "No", "No", "Yes", "No"],
    })


class TestGetSkiprows:
    def test_returns_correct_skiprows(self, tmp_path):
        path = make_raw_csv(tmp_path, blank_line_at=3)
        assert get_skiprows(path) == 4  # blank at index 3 → skip 4 rows

    def test_raises_on_no_blank_line(self, tmp_path):
        p = tmp_path / "no_blank.csv"
        p.write_text("col1,col2\n1,2\n3,4\n")
        with pytest.raises(ValueError):
            get_skiprows(str(p))


class TestCreateFeatures:
    def test_build_features_runs(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.build_features()
        assert len(cf.df) > 0

    def test_sin_cos_columns_created(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.create_sin_cos_features(["WindGustDir"])
        assert "WindGustDir_sin" in cf.df.columns
        assert "WindGustDir_cos" in cf.df.columns

    def test_sin_cos_values_in_range(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.create_sin_cos_features(["WindGustDir"])
        assert cf.df["WindGustDir_sin"].between(-1, 1).all()
        assert cf.df["WindGustDir_cos"].between(-1, 1).all()

    def test_lag_features_created(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.create_lag_features(["MinTemp"], lags=[1, 3])
        assert "MinTemp_lag_1" in cf.df.columns
        assert "MinTemp_lag_3" in cf.df.columns

    def test_time_features_created(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.create_time_features("Date")
        assert "dayofyear" in cf.df.columns
        assert cf.df["dayofyear"].between(1, 366).all()

    def test_dropped_columns_removed(self):
        df = make_weather_df()
        cf = CreateFeatures(df)
        cf.build_features()
        for col in ["Location", "WindGustDir", "Evaporation", "Sunshine"]:
            assert col not in cf.df.columns
