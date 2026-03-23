"""
utils/metrics.py
Performance metric computations using confirmed LAMP column schema.

All column names verified against schema probe (2026-03-04).
Policy references:
  - OTP: 2021 MBTA Service Delivery Policy
  - ETT: 2024 MBTA Service Delivery Policy (adopted Dec 19, 2024)
  - Headway: MBTA Annual Service Delivery Report
"""

import pandas as pd
import numpy as np

ETT_THRESHOLD_MIN = 5.0
OTP_THRESHOLD_SEC = 300
HEADWAY_TOLERANCE = 0.25

LINE_ORDER = ["Red", "Orange", "Green", "Blue"]


# ── OTP ───────────────────────────────────────────────────────────────────────

def otp_by_line(df: pd.DataFrame) -> pd.DataFrame:
    """OTP % grouped by line."""
    df = df.copy()
    df["is_on_time"] = df["is_on_time"].astype(float)

    agg = (
        df.groupby("line")["is_on_time"]
        .agg(on_time_trips="sum", total_trips="count")
        .reset_index()
    )

    agg["otp_pct"] = (agg["on_time_trips"] / agg["total_trips"] * 100).round(1)
    agg["line"] = pd.Categorical(agg["line"], categories=LINE_ORDER, ordered=True)

    return agg.sort_values("line").reset_index(drop=True)


def otp_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Daily OTP % by line."""
    df = df.copy()
    df["is_on_time"] = df["is_on_time"].astype(float)

    agg = (
        df.groupby(["date", "line"])["is_on_time"]
        .agg(on_time="sum", total="count")
        .reset_index()
    )

    agg["otp_pct"] = (agg["on_time"] / agg["total"] * 100).round(1)

    return agg.sort_values(["date", "line"]).reset_index(drop=True)


def otp_by_period(df: pd.DataFrame) -> pd.DataFrame:
    """OTP % split by Peak vs Off-Peak."""
    df = df.copy()
    df["is_on_time"] = df["is_on_time"].astype(float)

    agg = (
        df.groupby(["line", "period"])["is_on_time"]
        .agg(on_time="sum", total="count")
        .reset_index()
    )

    agg["otp_pct"] = (agg["on_time"] / agg["total"] * 100).round(1)
    agg = agg.rename(columns={"total": "total_trips"})
    agg["line"] = pd.Categorical(agg["line"], categories=LINE_ORDER, ordered=True)

    return agg.sort_values(["line", "period"]).reset_index(drop=True)


def otp_by_stop(df: pd.DataFrame, line: str) -> pd.DataFrame:
    """
    OTP % per stop for a given line — intermediate stops only.
    """
    last_seq = df.groupby("trip_id")["stop_sequence"].max().rename("max_seq")
    df_m = df.merge(last_seq, on="trip_id")

    line_df = df_m[
        (df_m["line"] == line) &
        (df_m["stop_sequence"] > 1) &
        (df_m["stop_sequence"] < df_m["max_seq"]) &
        (df_m["travel_time_seconds"].notna()) &
        (df_m["scheduled_travel_time"].notna())
    ].copy()

    line_df["is_on_time_num"] = line_df["is_on_time"].astype(float)

    agg = (
        line_df.groupby("parent_station")["is_on_time_num"]
        .agg(on_time="sum", total_trips="count")
        .reset_index()
    )

    agg["otp_pct"] = (agg["on_time"] / agg["total_trips"] * 100).round(1)

    return agg.sort_values("otp_pct").reset_index(drop=True)


# ── ETT ───────────────────────────────────────────────────────────────────────

def ett_by_line(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["ett_min"])

    agg = (
        clean.groupby("line")["ett_min"]
        .agg(
            avg_ett_min="mean",
            median_ett_min="median",
            p90_ett_min=lambda x: x.quantile(0.9),
        )
        .reset_index()
    )

    rel = (
        clean.groupby("line")["is_reliable"]
        .mean()
        .reset_index()
        .rename(columns={"is_reliable": "pct_reliable"})
    )

    agg = agg.merge(rel, on="line")

    agg["avg_ett_min"] = agg["avg_ett_min"].round(2)
    agg["median_ett_min"] = agg["median_ett_min"].round(2)
    agg["p90_ett_min"] = agg["p90_ett_min"].round(2)
    agg["pct_reliable"] = (agg["pct_reliable"] * 100).round(1)

    agg["line"] = pd.Categorical(agg["line"], categories=LINE_ORDER, ordered=True)

    return agg.sort_values("line").reset_index(drop=True)


def ett_trend(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["ett_min"])

    agg = (
        clean.groupby(["date", "line"])["ett_min"]
        .mean()
        .reset_index()
        .rename(columns={"ett_min": "avg_ett_min"})
    )

    agg["avg_ett_min"] = agg["avg_ett_min"].round(2)

    return agg.sort_values(["date", "line"]).reset_index(drop=True)


def ett_by_period(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["ett_min"])

    agg = (
        clean.groupby(["line", "period"])["ett_min"]
        .agg(
            avg_ett_min="mean",
            pct_reliable=lambda x: (x <= ETT_THRESHOLD_MIN).mean()
        )
        .reset_index()
    )

    agg["avg_ett_min"] = agg["avg_ett_min"].round(2)
    agg["pct_reliable"] = (agg["pct_reliable"] * 100).round(1)

    return agg.sort_values(["line", "period"]).reset_index(drop=True)


# ── Headway ───────────────────────────────────────────────────────────────────

def headway_by_line(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["headway_trunk_seconds", "scheduled_headway_trunk"])

    clean = clean[
        (clean["scheduled_headway_trunk"] > 0) &
        (clean["headway_trunk_seconds"] > 0)
    ].copy()

    clean["headway_ratio"] = (
        clean["headway_trunk_seconds"] / clean["scheduled_headway_trunk"]
    )

    clean["adherent"] = clean["headway_ratio"].between(
        1 - HEADWAY_TOLERANCE, 1 + HEADWAY_TOLERANCE
    )

    agg = (
        clean.groupby("line")
        .agg(
            avg_scheduled_sec=("scheduled_headway_trunk", "mean"),
            avg_actual_sec=("headway_trunk_seconds", "mean"),
            avg_gap_sec=("headway_gap_seconds", "mean"),
            pct_adherent=("adherent", "mean"),
        )
        .reset_index()
    )

    agg["avg_scheduled_min"] = (agg["avg_scheduled_sec"] / 60).round(1)
    agg["avg_actual_min"] = (agg["avg_actual_sec"] / 60).round(1)
    agg["avg_gap_sec"] = agg["avg_gap_sec"].round(1)
    agg["pct_adherent"] = (agg["pct_adherent"] * 100).round(1)

    agg["line"] = pd.Categorical(agg["line"], categories=LINE_ORDER, ordered=True)

    return agg.sort_values("line").reset_index(drop=True)[
        ["line", "avg_scheduled_min", "avg_actual_min", "avg_gap_sec", "pct_adherent"]
    ]


def headway_by_stop(df: pd.DataFrame, line: str) -> pd.DataFrame:
    last_seq = df.groupby("trip_id")["stop_sequence"].max().rename("max_seq")
    df_m = df.merge(last_seq, on="trip_id")

    clean = df_m[
        (df_m["line"] == line) &
        (df_m["stop_sequence"] > 1) &
        (df_m["stop_sequence"] < df_m["max_seq"])
    ].dropna(subset=["headway_trunk_seconds", "scheduled_headway_trunk"]).copy()

    clean = clean[
        (clean["scheduled_headway_trunk"] > 0) &
        (clean["headway_trunk_seconds"] > 0)
    ]

    agg = (
        clean.groupby("parent_station")
        .agg(
            avg_actual_sec=("headway_trunk_seconds", "mean"),
            avg_scheduled_sec=("scheduled_headway_trunk", "mean"),
        )
        .reset_index()
    )

    agg["avg_actual_min"] = (agg["avg_actual_sec"] / 60).round(1)
    agg["avg_scheduled_min"] = (agg["avg_scheduled_sec"] / 60).round(1)

    agg["headway_ratio_pct"] = (
        agg["avg_actual_sec"] / agg["avg_scheduled_sec"] * 100
    ).round(1)

    return agg.sort_values("headway_ratio_pct", ascending=False).reset_index(drop=True)[
        ["parent_station", "avg_actual_min", "avg_scheduled_min", "headway_ratio_pct"]
    ]


# ── KPI snapshot ─────────────────────────────────────────────

def kpi_snapshot(df: pd.DataFrame) -> dict:
    kpis = {
        "total_records": len(df),
        "days_covered": df["date"].nunique() if "date" in df.columns else 0,
        "otp_pct": None,
        "avg_ett_min": None,
        "pct_reliable": None,
        "pct_adherent": None,
    }

    if "is_on_time" in df.columns:
        kpis["otp_pct"] = round(df["is_on_time"].astype(float).mean() * 100, 1)

    if "ett_min" in df.columns:
        clean_ett = df["ett_min"].dropna()
        if not clean_ett.empty:
            kpis["avg_ett_min"] = round(clean_ett.mean(), 2)
            kpis["pct_reliable"] = round(
                (clean_ett <= ETT_THRESHOLD_MIN).mean() * 100, 1
            )

    clean_hw = df.dropna(subset=["headway_trunk_seconds", "scheduled_headway_trunk"])

    clean_hw = clean_hw[
        (clean_hw["scheduled_headway_trunk"] > 0) &
        (clean_hw["headway_trunk_seconds"] > 0)
    ]

    if not clean_hw.empty:
        ratio = (
            clean_hw["headway_trunk_seconds"] / clean_hw["scheduled_headway_trunk"]
        )

        kpis["pct_adherent"] = round(
            ratio.between(1 - HEADWAY_TOLERANCE, 1 + HEADWAY_TOLERANCE).mean() * 100, 1
        )

    return kpis