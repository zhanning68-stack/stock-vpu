import math

import numpy as np
import pandas as pd


def _get_limit_threshold(code: str, is_st: bool = False) -> float:
    if is_st:
        return 0.048
    if code.startswith("688") or code.startswith("300") or code.startswith("301"):
        return 0.198
    return 0.098


def _trimmed_mean(values: pd.Series, trim_ratio: float) -> float:
    sorted_values = values.sort_values().reset_index(drop=True)
    n = len(sorted_values)
    trim_count = math.floor(n * trim_ratio)
    if 2 * trim_count >= n:
        return sorted_values.mean()
    trimmed = sorted_values.iloc[trim_count : n - trim_count]
    return trimmed.mean()


def _extract_time_str(dt_value) -> str:
    if isinstance(dt_value, str):
        return dt_value
    if hasattr(dt_value, "strftime"):
        return dt_value.strftime("%H:%M")
    return str(dt_value)


def _extract_date(dt_value):
    if hasattr(dt_value, "date"):
        return dt_value.date()
    return pd.to_datetime(dt_value).date()


def clean_data(
    df: pd.DataFrame,
    config,
    code: str = "000001",
    is_st: bool = False,
) -> pd.DataFrame:
    df = df.copy()

    if "time" in df.columns:
        df["_time_str"] = df["time"].apply(_extract_time_str)
    else:
        df["_time_str"] = df["date"].apply(lambda x: _extract_time_str(x))

    df["_trade_date"] = df["date"].apply(_extract_date)

    threshold = _get_limit_threshold(code, is_st)

    daily_stats = df.groupby("_trade_date").agg(
        daily_high=("high", "max"),
        daily_low=("low", "min"),
        prev_close=("prev_close", "first"),
    )

    daily_stats["up_pct"] = (
        daily_stats["daily_high"] - daily_stats["prev_close"]
    ) / daily_stats["prev_close"]
    daily_stats["down_pct"] = (
        daily_stats["daily_low"] - daily_stats["prev_close"]
    ) / daily_stats["prev_close"]

    limit_days = daily_stats[
        (daily_stats["up_pct"] > threshold) | (daily_stats["down_pct"] < -threshold)
    ].index

    df = df[~df["_trade_date"].isin(limit_days)]

    if config.SKIP_FIRST_LAST:
        df = df[~df["_time_str"].isin(["09:30", "09:35", "14:55", "15:00"])]

    df = df[df["high"] != df["low"]]

    df = df[(df["high"] - df["low"]) >= config.MIN_PRICE_SPREAD]

    valid_counts = df.groupby("_trade_date").size()
    insufficient_days = valid_counts[valid_counts < config.MIN_VALID_UNITS].index

    df["insufficient_data"] = df["_trade_date"].isin(insufficient_days)

    return df


def calculate_unit_vpu(df: pd.DataFrame, config) -> pd.DataFrame:
    df = df.copy()

    valid_mask = ~df.get("insufficient_data", pd.Series(False, index=df.index))

    df["adj_spread"] = np.nan
    df["raw_spread"] = np.nan
    df["adj_units"] = np.nan
    df["raw_units"] = np.nan
    df["vpu_i"] = np.nan
    df["apu_i"] = np.nan
    df["direction"] = "neutral"

    df.loc[valid_mask, "adj_spread"] = (
        df.loc[valid_mask, "adj_high"] - df.loc[valid_mask, "adj_low"]
    )
    df.loc[valid_mask, "raw_spread"] = (
        df.loc[valid_mask, "high"] - df.loc[valid_mask, "low"]
    )

    adj_spread_valid = df.loc[valid_mask, "adj_spread"]
    raw_spread_valid = df.loc[valid_mask, "raw_spread"]

    df.loc[valid_mask, "adj_units"] = adj_spread_valid.apply(
        lambda s: max(1, math.ceil(s / config.PRICE_UNIT))
    )
    df.loc[valid_mask, "raw_units"] = raw_spread_valid.apply(
        lambda s: max(1, math.ceil(s / config.PRICE_UNIT))
    )

    df.loc[valid_mask, "vpu_i"] = (
        df.loc[valid_mask, "volume"] / df.loc[valid_mask, "adj_units"]
    )
    df.loc[valid_mask, "apu_i"] = (
        df.loc[valid_mask, "amount"] / df.loc[valid_mask, "raw_units"]
    )

    up_mask = valid_mask & (df["close"] > df["open"])
    down_mask = valid_mask & (df["close"] < df["open"])

    df.loc[up_mask, "direction"] = "up"
    df.loc[down_mask, "direction"] = "down"

    return df


def aggregate_daily(
    df: pd.DataFrame, config, code: str = "000001", is_st: bool = False
) -> pd.DataFrame:
    if "_trade_date" not in df.columns:
        df = df.copy()
        df["_trade_date"] = df["date"].apply(_extract_date)

    valid_df = df[~df.get("insufficient_data", pd.Series(False, index=df.index))]

    results = []

    for trade_date, day_group in valid_df.groupby("_trade_date"):
        day_vpu = day_group["vpu_i"].dropna()
        day_apu = day_group["apu_i"].dropna()

        if day_vpu.empty:
            continue

        vpu = _trimmed_mean(day_vpu, config.TRIM_RATIO)
        apu = _trimmed_mean(day_apu, config.TRIM_RATIO)

        vpu_up = np.nan
        vpu_down = np.nan

        if config.ENABLE_DIRECTION:
            up_bars = day_group[day_group["direction"] == "up"]["vpu_i"].dropna()
            down_bars = day_group[day_group["direction"] == "down"]["vpu_i"].dropna()

            if len(up_bars) >= 3:
                vpu_up = _trimmed_mean(up_bars, config.TRIM_RATIO)

            if len(down_bars) >= 3:
                vpu_down = _trimmed_mean(down_bars, config.TRIM_RATIO)

        close_price = day_group.iloc[-1]["close"]

        prev_close = day_group.iloc[0]["prev_close"]
        daily_high = day_group["high"].max()
        daily_low = day_group["low"].min()

        threshold = _get_limit_threshold(code, is_st)
        is_limit_up = (daily_high - prev_close) / prev_close > threshold
        is_limit_down = (daily_low - prev_close) / prev_close < -threshold

        results.append(
            {
                "date": trade_date,
                "vpu": vpu,
                "vpu_up": vpu_up,
                "vpu_down": vpu_down,
                "apu": apu,
                "close_price": close_price,
                "is_limit_up": is_limit_up,
                "is_limit_down": is_limit_down,
                "is_ex_dividend": False,
            }
        )

    if not results:
        return pd.DataFrame(
            columns=[
                "date",
                "vpu",
                "vpu_up",
                "vpu_down",
                "apu",
                "close_price",
                "is_limit_up",
                "is_limit_down",
                "is_ex_dividend",
            ]
        )

    return pd.DataFrame(results)


def calculate_moving_averages(df: pd.DataFrame, config) -> pd.DataFrame:
    df = df.copy()

    for period in config.MA_PERIODS:
        column_name = f"ma{period}"
        df[column_name] = df["vpu"].rolling(window=period, min_periods=1).mean()

    return df


def calculate_vpu(
    df: pd.DataFrame,
    config,
    code: str = "000001",
    is_st: bool = False,
) -> pd.DataFrame:
    cleaned = clean_data(df, config, code=code, is_st=is_st)
    with_unit_vpu = calculate_unit_vpu(cleaned, config)
    daily = aggregate_daily(with_unit_vpu, config, code=code, is_st=is_st)
    with_ma = calculate_moving_averages(daily, config)

    output_columns = [
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

    for col in output_columns:
        if col not in with_ma.columns:
            with_ma[col] = np.nan

    return with_ma[output_columns]
