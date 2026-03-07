import math
import os
import tempfile
from datetime import datetime, date, timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from config import Config, config
from calculator import (
    _get_limit_threshold,
    _trimmed_mean,
    _extract_time_str,
    _extract_date,
    clean_data,
    calculate_unit_vpu,
    aggregate_daily,
    calculate_moving_averages,
    calculate_vpu,
)
from visualizer import render_chart, render_apu_chart, export_csv, export_png
from data_fetcher import fetch_5min_kline


TIMES_5MIN = [
    "09:30",
    "09:35",
    "09:40",
    "09:45",
    "09:50",
    "09:55",
    "10:00",
    "10:05",
    "10:10",
    "10:15",
    "10:20",
    "10:25",
    "10:30",
    "10:35",
    "10:40",
    "10:45",
    "10:50",
    "10:55",
    "11:00",
    "11:05",
    "11:10",
    "11:15",
    "11:20",
    "11:25",
    "11:30",
    "13:00",
    "13:05",
    "13:10",
    "13:15",
    "13:20",
    "13:25",
    "13:30",
    "13:35",
    "13:40",
    "13:45",
    "13:50",
    "13:55",
    "14:00",
    "14:05",
    "14:10",
    "14:15",
    "14:20",
    "14:25",
    "14:30",
    "14:35",
    "14:40",
    "14:45",
    "14:50",
    "14:55",
    "15:00",
]


def make_mock_kline(n_days=5, bars_per_day=48, base_price=100.0, code="000001"):
    rows = []
    base_date = datetime(2025, 1, 6)
    prev_close = base_price - 0.5
    np.random.seed(42)

    for day_idx in range(n_days):
        current_date = base_date + timedelta(days=day_idx)
        day_str = current_date.strftime("%Y-%m-%d")
        day_prev_close = prev_close

        times_to_use = TIMES_5MIN[:bars_per_day]

        for i, t in enumerate(times_to_use):
            dt_str = f"{day_str} {t}:00"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

            noise = np.random.uniform(-0.3, 0.3)
            o = round(base_price + noise, 2)
            c = round(o + np.random.uniform(-0.2, 0.2), 2)
            h = round(max(o, c) + np.random.uniform(0.05, 0.15), 2)
            low = round(min(o, c) - np.random.uniform(0.05, 0.15), 2)
            vol = int(np.random.uniform(1000, 5000))
            amt = round(vol * (o + c) / 2, 2)

            rows.append(
                {
                    "date": dt,
                    "open": o,
                    "high": h,
                    "low": low,
                    "close": c,
                    "volume": vol,
                    "amount": amt,
                    "prev_close": day_prev_close,
                    "adj_open": o * 1.01,
                    "adj_high": h * 1.01,
                    "adj_low": low * 1.01,
                    "adj_close": c * 1.01,
                }
            )

        prev_close = rows[-1]["close"]
        base_price = prev_close

    return pd.DataFrame(rows)


def make_result_df(n_days=5):
    rows = []
    base_date = date(2025, 1, 6)
    np.random.seed(42)

    for i in range(n_days):
        d = base_date + timedelta(days=i)
        vpu = np.random.uniform(500, 2000)
        rows.append(
            {
                "date": d,
                "vpu": vpu,
                "vpu_up": vpu * 0.6,
                "vpu_down": vpu * 0.4,
                "apu": vpu * 100,
                "ma5": vpu,
                "ma10": vpu,
                "close_price": round(100 + np.random.uniform(-2, 2), 2),
                "is_limit_up": False,
                "is_limit_down": False,
                "is_ex_dividend": False,
            }
        )

    return pd.DataFrame(rows)


class TestConfig:
    def test_default_values(self):
        cfg = Config()
        assert cfg.PRICE_UNIT == 0.05
        assert cfg.TRIM_RATIO == 0.25
        assert cfg.MIN_VALID_UNITS == 10
        assert cfg.MIN_PRICE_SPREAD == 0.03
        assert cfg.MA_PERIODS == [5, 10]
        assert cfg.SKIP_FIRST_LAST is True
        assert cfg.ENABLE_DIRECTION is True

    def test_custom_values(self):
        cfg = Config(PRICE_UNIT=0.01, TRIM_RATIO=0.1, MIN_VALID_UNITS=5)
        assert cfg.PRICE_UNIT == 0.01
        assert cfg.TRIM_RATIO == 0.1
        assert cfg.MIN_VALID_UNITS == 5

    def test_global_config_instance(self):
        assert isinstance(config, Config)


class TestGetLimitThreshold:
    def test_main_board_000(self):
        assert _get_limit_threshold("000001") == pytest.approx(0.098)

    def test_main_board_600(self):
        assert _get_limit_threshold("600519") == pytest.approx(0.098)

    def test_star_market_688(self):
        assert _get_limit_threshold("688001") == pytest.approx(0.198)

    def test_chinext_300(self):
        assert _get_limit_threshold("300001") == pytest.approx(0.198)

    def test_chinext_301(self):
        assert _get_limit_threshold("301001") == pytest.approx(0.198)

    def test_st_stock(self):
        assert _get_limit_threshold("000001", is_st=True) == pytest.approx(0.048)

    def test_st_overrides_board(self):
        assert _get_limit_threshold("688001", is_st=True) == pytest.approx(0.048)


class TestTrimmedMean:
    def test_basic(self):
        vals = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = _trimmed_mean(vals, 0.2)
        expected = pd.Series([3, 4, 5, 6, 7, 8]).mean()
        assert result == pytest.approx(expected)

    def test_zero_trim(self):
        vals = pd.Series([1, 2, 3, 4, 5])
        assert _trimmed_mean(vals, 0.0) == pytest.approx(3.0)

    def test_high_trim_falls_back_to_mean(self):
        vals = pd.Series([1, 2, 3])
        result = _trimmed_mean(vals, 0.5)
        assert result == pytest.approx(2.0)

    def test_all_same_values(self):
        vals = pd.Series([5, 5, 5, 5])
        assert _trimmed_mean(vals, 0.25) == pytest.approx(5.0)

    def test_two_elements(self):
        vals = pd.Series([10, 20])
        result = _trimmed_mean(vals, 0.25)
        assert result == pytest.approx(15.0)

    def test_single_element(self):
        vals = pd.Series([42])
        assert _trimmed_mean(vals, 0.25) == pytest.approx(42.0)


class TestExtractTimeStr:
    def test_string_input(self):
        assert _extract_time_str("09:30") == "09:30"

    def test_datetime_input(self):
        dt = datetime(2025, 1, 6, 9, 30)
        assert _extract_time_str(dt) == "09:30"

    def test_other_type(self):
        result = _extract_time_str(12345)
        assert result == "12345"


class TestExtractDate:
    def test_datetime_input(self):
        dt = datetime(2025, 1, 6, 9, 30)
        assert _extract_date(dt) == date(2025, 1, 6)

    def test_string_input(self):
        assert _extract_date("2025-01-06") == date(2025, 1, 6)


class TestCleanData:
    cfg: Config = Config()

    def setup_method(self):
        self.cfg = Config()

    def test_excludes_limit_up_days(self):
        df = make_mock_kline(n_days=2, bars_per_day=20)
        day1_mask = df["date"].dt.date == date(2025, 1, 6)
        df.loc[day1_mask, "high"] = df.loc[day1_mask, "prev_close"] * 1.11
        result = clean_data(df, self.cfg, code="000001")
        remaining_dates = result["_trade_date"].unique()
        assert date(2025, 1, 6) not in remaining_dates

    def test_excludes_limit_down_days(self):
        df = make_mock_kline(n_days=2, bars_per_day=20)
        day1_mask = df["date"].dt.date == date(2025, 1, 6)
        df.loc[day1_mask, "low"] = df.loc[day1_mask, "prev_close"] * 0.88
        result = clean_data(df, self.cfg, code="000001")
        remaining_dates = result["_trade_date"].unique()
        assert date(2025, 1, 6) not in remaining_dates

    def test_excludes_first_last_5min(self):
        df = make_mock_kline(n_days=1, bars_per_day=50)
        result = clean_data(df, self.cfg)
        time_strs = result["_time_str"].unique()
        assert "09:30" not in time_strs
        assert "09:35" not in time_strs
        assert "14:55" not in time_strs
        assert "15:00" not in time_strs

    def test_skip_first_last_disabled(self):
        cfg = Config(SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=1, bars_per_day=50)
        result = clean_data(df, cfg)
        time_strs = result["_time_str"].unique()
        assert "09:30" in time_strs

    def test_excludes_zero_spread(self):
        df = make_mock_kline(n_days=1, bars_per_day=20)
        df.loc[10, "high"] = df.loc[10, "low"]
        result = clean_data(df, self.cfg)
        if 10 in result.index:
            assert result.loc[10, "high"] != result.loc[10, "low"]

    def test_excludes_small_spread(self):
        df = make_mock_kline(n_days=1, bars_per_day=20)
        df.loc[10, "high"] = df.loc[10, "low"] + 0.01
        result = clean_data(df, self.cfg)
        for _, row in result.iterrows():
            assert (row["high"] - row["low"]) >= self.cfg.MIN_PRICE_SPREAD

    def test_insufficient_data_marking(self):
        cfg = Config(MIN_VALID_UNITS=100, SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=1, bars_per_day=20)
        result = clean_data(df, cfg)
        assert bool(result["insufficient_data"].all())

    def test_sufficient_data_not_marked(self):
        cfg = Config(MIN_VALID_UNITS=5, SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=1, bars_per_day=20)
        result = clean_data(df, cfg)
        if not result.empty:
            assert not bool(result["insufficient_data"].all())

    def test_688_limit_threshold(self):
        df = make_mock_kline(n_days=2, bars_per_day=20)
        day1_mask = df["date"].dt.date == date(2025, 1, 6)
        df.loc[day1_mask, "high"] = df.loc[day1_mask, "prev_close"] * 1.15
        result = clean_data(df, self.cfg, code="688001")
        remaining_dates = result["_trade_date"].unique()
        assert date(2025, 1, 6) in remaining_dates


class TestCalculateUnitVpu:
    cfg: Config = Config()

    def setup_method(self):
        self.cfg = Config()

    def test_discrete_ceil_calculation(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.12,
                    "low": 100.0,
                    "close": 100.05,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.12,
                    "adj_low": 100.0,
                    "adj_close": 100.05,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert result.iloc[0]["adj_units"] == math.ceil(0.12 / 0.05)
        assert result.iloc[0]["adj_units"] == 3
        assert result.iloc[0]["vpu_i"] == pytest.approx(3000 / 3)

    def test_vpu_formula(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.25,
                    "low": 100.0,
                    "close": 100.10,
                    "volume": 4000,
                    "amount": 400000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.25,
                    "adj_low": 100.0,
                    "adj_close": 100.10,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        adj_spread = 100.25 - 100.0
        adj_units = max(1, math.ceil(adj_spread / self.cfg.PRICE_UNIT))
        assert result.iloc[0]["adj_units"] == adj_units
        assert result.iloc[0]["vpu_i"] == pytest.approx(4000 / adj_units)

    def test_apu_uses_raw_units(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.15,
                    "low": 100.0,
                    "close": 100.10,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 101.0,
                    "adj_high": 101.25,
                    "adj_low": 101.0,
                    "adj_close": 101.10,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        raw_spread = 100.15 - 100.0
        raw_units = max(1, math.ceil(raw_spread / self.cfg.PRICE_UNIT))
        assert result.iloc[0]["raw_units"] == raw_units
        assert result.iloc[0]["apu_i"] == pytest.approx(300000 / raw_units)

    def test_direction_up(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.20,
                    "low": 99.90,
                    "close": 100.10,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.20,
                    "adj_low": 99.90,
                    "adj_close": 100.10,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert result.iloc[0]["direction"] == "up"

    def test_direction_down(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.10,
                    "high": 100.20,
                    "low": 99.90,
                    "close": 100.0,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.10,
                    "adj_high": 100.20,
                    "adj_low": 99.90,
                    "adj_close": 100.0,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert result.iloc[0]["direction"] == "down"

    def test_direction_neutral(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.20,
                    "low": 99.90,
                    "close": 100.0,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.20,
                    "adj_low": 99.90,
                    "adj_close": 100.0,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert result.iloc[0]["direction"] == "neutral"

    def test_insufficient_data_skipped(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.20,
                    "low": 99.90,
                    "close": 100.10,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.20,
                    "adj_low": 99.90,
                    "adj_close": 100.10,
                    "insufficient_data": True,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert pd.isna(result.iloc[0]["vpu_i"])

    def test_min_unit_is_one(self):
        df = pd.DataFrame(
            [
                {
                    "date": datetime(2025, 1, 6, 10, 0),
                    "open": 100.0,
                    "high": 100.01,
                    "low": 100.0,
                    "close": 100.005,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": 100.0,
                    "adj_high": 100.01,
                    "adj_low": 100.0,
                    "adj_close": 100.005,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": "10:00",
                }
            ]
        )
        result = calculate_unit_vpu(df, self.cfg)
        assert result.iloc[0]["adj_units"] >= 1


class TestAggregateDaily:
    cfg: Config = Config()

    def setup_method(self):
        self.cfg = Config()

    def _make_day_bars(self, n_bars=20, direction_split=True):
        rows = []
        for i in range(n_bars):
            t = f"10:{i:02d}"
            if direction_split and i < n_bars // 2:
                o, c = 100.0, 100.10
            elif direction_split:
                o, c = 100.10, 100.0
            else:
                o, c = 100.0, 100.10

            rows.append(
                {
                    "date": datetime(2025, 1, 6, 10, i),
                    "open": o,
                    "high": 100.20,
                    "low": 99.90,
                    "close": c,
                    "volume": 3000,
                    "amount": 300000,
                    "prev_close": 99.5,
                    "adj_open": o,
                    "adj_high": 100.20,
                    "adj_low": 99.90,
                    "adj_close": c,
                    "insufficient_data": False,
                    "_trade_date": date(2025, 1, 6),
                    "_time_str": t,
                    "vpu_i": 500.0 + i * 10,
                    "apu_i": 50000.0 + i * 1000,
                    "direction": "up" if c > o else ("down" if c < o else "neutral"),
                    "adj_units": 6,
                    "raw_units": 6,
                    "adj_spread": 0.30,
                    "raw_spread": 0.30,
                }
            )
        return pd.DataFrame(rows)

    def test_produces_daily_row(self):
        df = self._make_day_bars(20)
        result = aggregate_daily(df, self.cfg)
        assert len(result) == 1
        assert result.iloc[0]["date"] == date(2025, 1, 6)

    def test_vpu_is_trimmed_mean(self):
        df = self._make_day_bars(20)
        result = aggregate_daily(df, self.cfg)
        expected = _trimmed_mean(pd.Series(df["vpu_i"]), self.cfg.TRIM_RATIO)
        assert result.iloc[0]["vpu"] == pytest.approx(expected)

    def test_vpu_up_down_split(self):
        df = self._make_day_bars(20, direction_split=True)
        result = aggregate_daily(df, self.cfg)
        assert not pd.isna(result.iloc[0]["vpu_up"])
        assert not pd.isna(result.iloc[0]["vpu_down"])

    def test_vpu_up_nan_when_few_bars(self):
        df = self._make_day_bars(20, direction_split=False)
        up_count = (df["direction"] == "up").sum()
        assert up_count >= 3
        df.loc[df.index[:18], "direction"] = "down"
        remaining_up = (df["direction"] == "up").sum()
        if remaining_up < 3:
            result = aggregate_daily(df, self.cfg)
            assert pd.isna(result.iloc[0]["vpu_up"])

    def test_direction_disabled(self):
        cfg = Config(ENABLE_DIRECTION=False)
        df = self._make_day_bars(20)
        result = aggregate_daily(df, cfg)
        assert pd.isna(result.iloc[0]["vpu_up"])
        assert pd.isna(result.iloc[0]["vpu_down"])

    def test_limit_up_flag(self):
        df = self._make_day_bars(20)
        df["high"] = df["prev_close"] * 1.11
        result = aggregate_daily(df, self.cfg, code="000001")
        assert bool(result.iloc[0]["is_limit_up"]) is True

    def test_limit_down_flag(self):
        df = self._make_day_bars(20)
        df["low"] = df["prev_close"] * 0.88
        result = aggregate_daily(df, self.cfg, code="000001")
        assert bool(result.iloc[0]["is_limit_down"]) is True

    def test_empty_input(self):
        df = pd.DataFrame(
            {
                "date": pd.Series(dtype="datetime64[ns]"),
                "open": pd.Series(dtype="float64"),
                "high": pd.Series(dtype="float64"),
                "low": pd.Series(dtype="float64"),
                "close": pd.Series(dtype="float64"),
                "volume": pd.Series(dtype="float64"),
                "amount": pd.Series(dtype="float64"),
                "prev_close": pd.Series(dtype="float64"),
                "adj_open": pd.Series(dtype="float64"),
                "adj_high": pd.Series(dtype="float64"),
                "adj_low": pd.Series(dtype="float64"),
                "adj_close": pd.Series(dtype="float64"),
                "insufficient_data": pd.Series(dtype="bool"),
                "_trade_date": pd.Series(dtype="object"),
                "_time_str": pd.Series(dtype="str"),
                "vpu_i": pd.Series(dtype="float64"),
                "apu_i": pd.Series(dtype="float64"),
                "direction": pd.Series(dtype="str"),
                "adj_units": pd.Series(dtype="float64"),
                "raw_units": pd.Series(dtype="float64"),
                "adj_spread": pd.Series(dtype="float64"),
                "raw_spread": pd.Series(dtype="float64"),
            }
        )
        result = aggregate_daily(df, self.cfg)
        assert result.empty

    def test_close_price_is_last_bar(self):
        df = self._make_day_bars(20)
        df.loc[df.index[-1], "close"] = 888.88
        result = aggregate_daily(df, self.cfg)
        assert result.iloc[0]["close_price"] == pytest.approx(888.88)


class TestCalculateMovingAverages:
    cfg: Config = Config()

    def setup_method(self):
        self.cfg = Config()

    def test_ma5_ma10_columns_exist(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-06", periods=15),
                "vpu": range(15),
            }
        )
        result = calculate_moving_averages(df, self.cfg)
        assert "ma5" in result.columns
        assert "ma10" in result.columns

    def test_ma5_value(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-06", periods=10),
                "vpu": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            }
        )
        result = calculate_moving_averages(df, self.cfg)
        assert result.iloc[4]["ma5"] == pytest.approx(30.0)
        assert result.iloc[5]["ma5"] == pytest.approx(40.0)

    def test_ma10_value(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-06", periods=10),
                "vpu": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            }
        )
        result = calculate_moving_averages(df, self.cfg)
        assert result.iloc[9]["ma10"] == pytest.approx(55.0)

    def test_ma_min_periods_1(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-06", periods=3),
                "vpu": [10, 20, 30],
            }
        )
        result = calculate_moving_averages(df, self.cfg)
        assert result.iloc[0]["ma5"] == pytest.approx(10.0)
        assert result.iloc[1]["ma5"] == pytest.approx(15.0)


class TestCalculateVpuIntegration:
    def test_end_to_end(self):
        cfg = Config(MIN_VALID_UNITS=5, SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=3, bars_per_day=20)
        result = calculate_vpu(df, cfg, code="000001")
        assert not result.empty
        expected_cols = [
            "date",
            "vpu",
            "vpu_up",
            "vpu_down",
            "apu",
            "ma5",
            "ma10",
            "close_price",
            "is_limit_up",
            "is_limit_down",
            "is_ex_dividend",
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_output_column_order(self):
        cfg = Config(MIN_VALID_UNITS=5, SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=3, bars_per_day=20)
        result = calculate_vpu(df, cfg)
        expected_order = [
            "date",
            "vpu",
            "vpu_up",
            "vpu_down",
            "apu",
            "ma5",
            "ma10",
            "close_price",
            "is_limit_up",
            "is_limit_down",
            "is_ex_dividend",
        ]
        assert list(result.columns) == expected_order

    def test_vpu_values_positive(self):
        cfg = Config(MIN_VALID_UNITS=5, SKIP_FIRST_LAST=False)
        df = make_mock_kline(n_days=3, bars_per_day=20)
        result = calculate_vpu(df, cfg)
        assert (result["vpu"] > 0).all()


class TestDataFetcher:
    def _make_unadjusted_df(self, n=10):
        base = datetime(2025, 1, 6, 10, 0)
        rows = []
        for i in range(n):
            rows.append(
                {
                    "day": (base + timedelta(minutes=5 * i)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "open": 100.0 + i * 0.1,
                    "close": 100.05 + i * 0.1,
                    "high": 100.10 + i * 0.1,
                    "low": 99.95 + i * 0.1,
                    "volume": 1000 + i * 100,
                    "amount": 100000 + i * 10000,
                }
            )
        return pd.DataFrame(rows)

    def _make_adjusted_df(self, n=10):
        base = datetime(2025, 1, 6, 10, 0)
        rows = []
        for i in range(n):
            rows.append(
                {
                    "day": (base + timedelta(minutes=5 * i)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "open": 101.0 + i * 0.1,
                    "close": 101.05 + i * 0.1,
                    "high": 101.10 + i * 0.1,
                    "low": 100.95 + i * 0.1,
                }
            )
        return pd.DataFrame(rows)

    def _make_daily_df(self):
        rows = []
        base = date(2025, 1, 2)
        for i in range(5):
            d = base + timedelta(days=i)
            rows.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "open": 99.0 + i,
                    "close": 99.5 + i,
                    "high": 100.0 + i,
                    "low": 98.5 + i,
                    "volume": 50000,
                    "amount": 5000000,
                }
            )
        return pd.DataFrame(rows)

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_daily")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_column_renaming(self, mock_min, mock_daily, mock_sleep):
        unadj = self._make_unadjusted_df()
        adj = self._make_adjusted_df()
        daily = self._make_daily_df()
        mock_min.side_effect = [unadj, adj]
        mock_daily.return_value = daily

        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        expected_cols = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "prev_close",
            "adj_open",
            "adj_high",
            "adj_low",
            "adj_close",
        ]
        assert list(result.columns) == expected_cols

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_daily")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_prev_close_mapped(self, mock_min, mock_daily, mock_sleep):
        unadj = self._make_unadjusted_df()
        adj = self._make_adjusted_df()
        daily = self._make_daily_df()
        mock_min.side_effect = [unadj, adj]
        mock_daily.return_value = daily

        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        assert "prev_close" in result.columns
        assert not bool(result["prev_close"].isna().all())

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_empty_when_no_data(self, mock_min, mock_sleep):
        mock_min.return_value = pd.DataFrame()
        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        assert result.empty

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_empty_on_none(self, mock_min, mock_sleep):
        mock_min.return_value = None
        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        assert result.empty

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_daily")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_date_filtering(self, mock_min, mock_daily, mock_sleep):
        unadj = self._make_unadjusted_df()
        adj = self._make_adjusted_df()
        daily = self._make_daily_df()
        mock_min.side_effect = [unadj, adj]
        mock_daily.return_value = daily

        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        if not result.empty:
            assert (result["date"] >= pd.to_datetime("2025-01-06")).all()
            assert (result["date"] <= pd.to_datetime("2025-01-07")).all()

    @patch("data_fetcher.time.sleep")
    @patch("data_fetcher.ak.stock_zh_a_minute")
    def test_exception_returns_empty(self, mock_min, mock_sleep):
        mock_min.side_effect = Exception("network error")
        result = fetch_5min_kline("000001", "2025-01-06", "2025-01-06")
        assert result.empty


class TestVisualizer:
    result_df: pd.DataFrame = pd.DataFrame()

    def setup_method(self):
        self.result_df = make_result_df(10)

    def test_render_chart_structure(self):
        chart = render_chart(self.result_df, stock_code="600519")
        assert "title" in chart
        assert "series" in chart
        assert "yAxis" in chart
        assert "xAxis" in chart
        assert "tooltip" in chart
        assert len(chart["series"]) == 4
        assert "600519" in chart["title"]["text"]

    def test_render_chart_no_code(self):
        chart = render_chart(self.result_df)
        assert "VPU" in chart["title"]["text"]

    def test_render_chart_series_names(self):
        chart = render_chart(self.result_df, stock_code="600519")
        series_names = [s["name"] for s in chart["series"]]
        assert "VPU_Up (抛压)" in series_names
        assert "VPU_Down (支撑)" in series_names
        assert "MA5" in series_names
        assert "收盘价" in series_names

    def test_render_chart_data_length(self):
        chart = render_chart(self.result_df, stock_code="600519")
        n = len(self.result_df)
        for s in chart["series"]:
            assert len(s["data"]) == n

    def test_render_apu_chart_structure(self):
        chart = render_apu_chart(self.result_df, stock_code="600519")
        assert "title" in chart
        assert "series" in chart
        assert len(chart["series"]) == 2
        assert "APU" in chart["title"]["text"]

    def test_render_apu_chart_series_names(self):
        chart = render_apu_chart(self.result_df)
        series_names = [s["name"] for s in chart["series"]]
        assert "APU (成交额)" in series_names
        assert "收盘价" in series_names

    def test_render_chart_dual_yaxis(self):
        chart = render_chart(self.result_df)
        assert len(chart["yAxis"]) == 2

    def test_export_csv_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.csv")
            export_csv(self.result_df, path)
            assert os.path.exists(path)
            loaded = pd.read_csv(path)
            assert "date" in loaded.columns
            assert "vpu" in loaded.columns
            assert "apu" in loaded.columns
            assert len(loaded) == len(self.result_df)

    def test_export_csv_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.csv")
            export_csv(self.result_df, path)
            loaded = pd.read_csv(path)
            expected = [
                "date",
                "vpu",
                "vpu_up",
                "vpu_down",
                "apu",
                "ma5",
                "ma10",
                "close_price",
                "is_limit_up",
                "is_limit_down",
                "is_ex_dividend",
            ]
            assert list(loaded.columns) == expected

    def test_export_png_creates_file(self):
        import matplotlib

        matplotlib.use("Agg")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.png")
            export_png(self.result_df, path, stock_code="600519")
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
