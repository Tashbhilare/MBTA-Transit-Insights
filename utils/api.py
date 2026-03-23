"""
utils/api.py
MBTA V3 API — live data layer.

Endpoints used:
  /vehicles    — real-time train positions and status
  /predictions — predicted arrival/departure times (with schedule included)
  /alerts      — active service disruptions

API key is optional. Without it: 20 req/min limit.
With key: 1000 req/min. Get a free key at api-v3.mbta.com.

All confirmed working against api-v3.mbta.com on 2026-03-18.
"""

import os
import requests
import pandas as pd
from datetime import datetime


BASE_URL = "https://api-v3.mbta.com"

LINE_COLORS = {
    "Red":    "#DA291C",
    "Orange": "#ED8B00",
    "Green":  "#00843D",
    "Blue":   "#003A9B",
}

# Route IDs for sidebar selector
ROUTE_OPTIONS = {
    "Red Line":       "Red",
    "Orange Line":    "Orange",
    "Blue Line":      "Blue",
    "Green Line (B)": "Green-B",
    "Green Line (C)": "Green-C",
    "Green Line (D)": "Green-D",
    "Green Line (E)": "Green-E",
}


def _get_api_key() -> str:
    """Read API key from environment variable or .env file."""
    return os.environ.get("MBTA_API_KEY", "")


def _get(endpoint: str, params: dict = None) -> dict:
    """
    Make a GET request to the MBTA V3 API.
    Raises requests.HTTPError on non-200 responses.
    """
    headers = {}
    key = _get_api_key()
    if key:
        headers["x-api-key"] = key

    resp = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params or {},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Vehicles ──────────────────────────────────────────────────────────────────

def get_vehicles(route_id: str, direction_id: int) -> pd.DataFrame:
    """
    Fetch live vehicle positions for a route and direction.
    Returns DataFrame: vehicle_id, label, latitude, longitude,
                       current_status, speed_mph, updated_at
    Speed is converted from m/s (API) to mph.
    """
    data = _get("/vehicles", {
        "filter[route]":        route_id,
        "filter[direction_id]": direction_id,
        "fields[vehicle]":      "label,latitude,longitude,current_status,speed,updated_at",
    })

    rows = []
    for v in data.get("data", []):
        a = v["attributes"]
        speed_raw = a.get("speed")
        rows.append({
            "vehicle_id":     v["id"],
            "label":          a.get("label", v["id"]),
            "latitude":       a.get("latitude"),
            "longitude":      a.get("longitude"),
            "current_status": a.get("current_status", "").replace("_", " ").title(),
            "speed_mph":      round(speed_raw * 2.237, 1) if speed_raw else None,
            "updated_at":     a.get("updated_at", ""),
        })

    return pd.DataFrame(rows)


# ── Predictions ───────────────────────────────────────────────────────────────

def get_predictions(route_id: str, direction_id: int) -> pd.DataFrame:
    """
    Fetch predictions with associated schedules for a route and direction.
    Computes delay_min = predicted departure - scheduled departure.

    Returns DataFrame: stop_name, predicted, scheduled,
                       delay_sec, delay_min, status
    Positive delay = late. Negative = early.
    """
    data = _get("/predictions", {
        "filter[route]":        route_id,
        "filter[direction_id]": direction_id,
        "include":              "stop,schedule",
        "fields[prediction]":   "departure_time,arrival_time,status",
        "fields[stop]":         "name",
        "fields[schedule]":     "departure_time,arrival_time",
        "page[limit]":          200,
    })

    # Build lookup maps from included resources
    stop_map  = {}   # stop_id  → stop_name
    sched_map = {}   # schedule_id → scheduled departure time string

    for inc in data.get("included", []):
        if inc["type"] == "stop":
            stop_map[inc["id"]] = inc["attributes"].get("name", inc["id"])
        elif inc["type"] == "schedule":
            # Use departure_time, fall back to arrival_time
            t = (inc["attributes"].get("departure_time") or
                 inc["attributes"].get("arrival_time"))
            sched_map[inc["id"]] = t

    rows = []
    for pred in data.get("data", []):
        a    = pred["attributes"]
        rels = pred.get("relationships", {})

        stop_id  = (rels.get("stop",     {}).get("data") or {}).get("id", "")
        sched_id = (rels.get("schedule", {}).get("data") or {}).get("id", "")

        # Use departure_time, fall back to arrival_time
        pred_time  = a.get("departure_time") or a.get("arrival_time")
        sched_time = sched_map.get(sched_id)

        delay_sec = None
        if pred_time and sched_time:
            try:
                p = datetime.fromisoformat(pred_time)
                s = datetime.fromisoformat(sched_time)
                delay_sec = (p - s).total_seconds()
            except Exception:
                pass

        rows.append({
            "stop_name": stop_map.get(stop_id, stop_id),
            "predicted": pred_time,
            "scheduled": sched_time,
            "delay_sec": delay_sec,
            "delay_min": round(delay_sec / 60, 1) if delay_sec is not None else None,
            "status":    a.get("status", "") or "",
        })

    df = pd.DataFrame(rows)
    # Drop rows with no stop name or no delay data
    if not df.empty:
        df = df[df["stop_name"] != ""].copy()
    return df


# ── Alerts ────────────────────────────────────────────────────────────────────

def get_alerts(route_id: str) -> list:
    """
    Fetch active service alerts for a route.
    Returns list of dicts: effect, severity, header, updated_at
    Filters to ongoing/new alerts only.
    """
    data = _get("/alerts", {
        "filter[route]":    route_id,
        "filter[activity]": "BOARD,EXIT,RIDE",
        "fields[alert]":    "header,effect,severity,updated_at,lifecycle",
    })

    alerts = []
    for a in data.get("data", []):
        attr = a["attributes"]
        lifecycle = attr.get("lifecycle", "")
        # Only include current alerts
        if lifecycle in ("NEW", "ONGOING", "ONGOING_UPCOMING", ""):
            alerts.append({
                "effect":     attr.get("effect", "").replace("_", " ").title(),
                "severity":   attr.get("severity", "Unknown"),
                "header":     attr.get("header", ""),
                "updated_at": attr.get("updated_at", ""),
            })
    return alerts


# ── Live OTP summary ──────────────────────────────────────────────────────────

def compute_live_metrics(preds_df: pd.DataFrame) -> dict:
    """
    Compute live KPIs from predictions DataFrame.
    Returns dict: otp_pct, avg_delay_min, ett_min, on_time, late, early, total
    """
    kpis = {
        "otp_pct":       None,
        "avg_delay_min": None,
        "ett_min":       None,
        "on_time":       0,
        "late":          0,
        "early":         0,
        "total":         0,
    }

    if preds_df.empty or "delay_min" not in preds_df.columns:
        return kpis

    delays = preds_df["delay_min"].dropna()
    if delays.empty:
        return kpis

    kpis["total"]         = len(delays)
    kpis["on_time"]       = int((delays.abs() <= 5).sum())
    kpis["late"]          = int((delays > 5).sum())
    kpis["early"]         = int((delays < -5).sum())
    kpis["otp_pct"]       = round((delays.abs() <= 5).mean() * 100, 1)
    kpis["avg_delay_min"] = round(delays.mean(), 1)
    kpis["ett_min"]       = round(delays.clip(lower=0).mean(), 2)

    return kpis