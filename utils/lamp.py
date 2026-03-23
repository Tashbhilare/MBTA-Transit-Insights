"""
utils/lamp.py
LAMP data loader — downloads and caches MBTA performance parquet files.

Data source: https://performancedata.mbta.com
These are the same datasets OPMI uses in Tableau for the
Annual Service Delivery Report and MassDOT Tracker.

Confirmed column schema (2026-03-04):
  travel_time_seconds      — actual travel time
  scheduled_travel_time    — planned travel time
  headway_trunk_seconds    — actual trunk headway
  headway_branch_seconds   — actual branch headway
  scheduled_headway_trunk  — planned trunk headway
  scheduled_headway_branch — planned branch headway
  trunk_route_id           — line level: Red, Orange, Green, Blue
  route_id                 — branch level: Green-B, Red, etc.
  start_time               — seconds after midnight (4am=14400)
  service_date             — integer YYYYMMDD
  direction_id             — bool (False=0, True=1)
  parent_station           — GTFS parent station id
"""

import io
import datetime
import urllib.request
import pandas as pd

LAMP_BASE   = "https://performancedata.mbta.com/lamp"
SUBWAY_LINES = ["Red", "Orange", "Green", "Blue"]

# Peak periods per 2024 Service Delivery Policy
# start_time is seconds after midnight
PEAK_AM_START = 6.5  * 3600   # 6:30 AM
PEAK_AM_END   = 9.0  * 3600   # 9:00 AM
PEAK_PM_START = 15.5 * 3600   # 3:30 PM
PEAK_PM_END   = 18.5 * 3600   # 6:30 PM

LINE_COLORS = {
    "Red":    "#DA291C",
    "Orange": "#ED8B00",
    "Green":  "#00843D",
    "Blue":   "#003A9B",
}


def _fetch_parquet(url: str) -> pd.DataFrame:
    """Download a parquet file and return as DataFrame."""
    import pyarrow.parquet as pq
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return pq.read_table(io.BytesIO(data)).to_pandas()


def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add computed columns used by all metrics.
    Called once after loading raw LAMP data.
    """
    # ── service_date → proper date ────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["service_date"].astype(str), format="%Y%m%d")

    # ── line (trunk) — what we group by for line-level charts ────────────────
    df["line"] = df["trunk_route_id"]

    # ── direction_id bool → int ───────────────────────────────────────────────
    df["direction_id_int"] = df["direction_id"].astype(int)

    # ── peak / off-peak flag ──────────────────────────────────────────────────
    t = df["start_time"]
    df["is_peak"] = (
        t.between(PEAK_AM_START, PEAK_AM_END) |
        t.between(PEAK_PM_START, PEAK_PM_END)
    )
    df["period"] = df["is_peak"].map({True: "Peak", False: "Off-Peak"})

    # ── hour of day ───────────────────────────────────────────────────────────
    df["hour"] = (df["start_time"] // 3600).clip(upper=23).astype(int)

    # ── OTP flag: within ±5 min of scheduled travel time ─────────────────────
    has_tt = df["travel_time_seconds"].notna() & df["scheduled_travel_time"].notna()
    df["delay_seconds"] = float("nan")
    df.loc[has_tt, "delay_seconds"] = (
        df.loc[has_tt, "travel_time_seconds"] -
        df.loc[has_tt, "scheduled_travel_time"]
    )
    df["is_on_time"] = df["delay_seconds"].abs().le(300).where(df["delay_seconds"].notna())

    # ── ETT (excess trip time, clipped at 0) ──────────────────────────────────
    df["ett_seconds"] = df["delay_seconds"].clip(lower=0)
    df["ett_min"]     = df["ett_seconds"] / 60
    df["is_reliable"] = df["ett_min"] <= 5.0  # 2024 SDP threshold

    # ── headway gap (actual - scheduled, trunk) ───────────────────────────────
    has_hw = df["headway_trunk_seconds"].notna() & df["scheduled_headway_trunk"].notna()
    df["headway_gap_seconds"] = float("nan")
    df.loc[has_hw, "headway_gap_seconds"] = (
        df.loc[has_hw, "headway_trunk_seconds"] -
        df.loc[has_hw, "scheduled_headway_trunk"]
    )

    return df


def load_lamp_days(days_back: int = 30) -> pd.DataFrame:
    """
    Download and concatenate LAMP OTP parquet files for the last N days.
    Skips dates that are not yet published (LAMP has ~2 day lag).
    Returns a clean DataFrame with all derived columns added.
    """
    today  = datetime.date.today()
    frames = []
    failed = []

    # Start 3 days back to account for LAMP publication lag
    end_date   = today - datetime.timedelta(days=3)
    start_date = today - datetime.timedelta(days=days_back + 3)

    dates = pd.date_range(start_date, end_date, freq="D")
    print(f"Loading {len(dates)} days of LAMP data ({start_date} to {end_date})...")

    for dt in dates:
        date_str = dt.strftime("%Y-%m-%d")
        url = (
            f"{LAMP_BASE}/subway-on-time-performance-v1/"
            f"{date_str}-subway-on-time-performance-v1.parquet"
        )
        try:
            df = _fetch_parquet(url)
            # Filter to rapid transit only (exclude Mattapan)
            df = df[df["trunk_route_id"].isin(SUBWAY_LINES)].copy()
            frames.append(df)
            print(f"  ✓ {date_str} — {len(df):,} rows")
        except Exception as e:
            failed.append(date_str)
            print(f"  ✗ {date_str} — skipped ({e})")

    if not frames:
        raise RuntimeError("No LAMP data loaded. Check internet connection.")

    raw = pd.concat(frames, ignore_index=True)
    df  = _add_derived_columns(raw)

    print(f"\nLoaded: {len(df):,} rows across {df['date'].nunique()} days")
    print(f"Lines:  {sorted(df['line'].unique())}")
    print(f"Failed: {len(failed)} dates")

    return df


def load_static_stops() -> pd.DataFrame:
    """Load LAMP static stops — station names and coordinates."""
    url = f"{LAMP_BASE}/tableau/rail/LAMP_static_stops.parquet"
    df  = _fetch_parquet(url)
    keep = [c for c in ["stop_id", "stop_name", "parent_station",
                         "stop_lat", "stop_lon"] if c in df.columns]
    return df[keep].drop_duplicates(subset=["stop_id"])


def load_static_routes() -> pd.DataFrame:
    """Load LAMP static routes — route names."""
    url = f"{LAMP_BASE}/tableau/rail/LAMP_static_routes.parquet"
    return _fetch_parquet(url)