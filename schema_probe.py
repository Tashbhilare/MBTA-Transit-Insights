"""
Step 1: Schema probe
Run this before anything else.
Downloads one day of LAMP data and prints exact column names, dtypes, and sample values.
This is the contract every other file will be built against.

Usage:
    pip install pyarrow pandas
    python schema_probe.py
"""

import urllib.request
import datetime
import io
import sys

def probe(url, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  {url}")
    print('='*60)
    try:
        import pyarrow.parquet as pq
        print("  Downloading...", end=" ", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        print(f"({len(data)//1024:,} KB)")
        table = pq.read_table(io.BytesIO(data))
        df = table.to_pandas()
        print(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
        print(f"\n  {'Column':<45} {'Dtype':<15} {'Sample value'}")
        print(f"  {'-'*45} {'-'*15} {'-'*30}")
        for col in df.columns:
            dtype  = str(df[col].dtype)
            sample = df[col].dropna()
            sample = str(sample.iloc[0]) if not sample.empty else "N/A"
            print(f"  {col:<45} {dtype:<15} {sample[:50]}")
        return df
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return None

# Use 14 days ago — guaranteed to be published by LAMP
target = (datetime.date.today() - datetime.timedelta(days=14)).strftime("%Y-%m-%d")
print(f"Target date: {target}")

# ── 1. Daily OTP file (the main one) ─────────────────────────────────────────
df_otp = probe(
    f"https://performancedata.mbta.com/lamp/subway-on-time-performance-v1/"
    f"{target}-subway-on-time-performance-v1.parquet",
    f"LAMP Subway OTP — {target}"
)

if df_otp is not None:
    print(f"\n  >> Unique route_id values: {sorted(df_otp['route_id'].unique()) if 'route_id' in df_otp.columns else 'N/A'}")
    if 'peak_offpeak_ind' in df_otp.columns:
        print(f"  >> peak_offpeak_ind values: {df_otp['peak_offpeak_ind'].unique()}")
    if 'is_on_time' in df_otp.columns:
        otp = df_otp['is_on_time'].mean() * 100
        print(f"  >> System OTP that day: {otp:.1f}%")

# ── 2. Static stops ───────────────────────────────────────────────────────────
probe(
    "https://performancedata.mbta.com/lamp/tableau/rail/LAMP_static_stops.parquet",
    "LAMP Static Stops"
)

# ── 3. Static routes ──────────────────────────────────────────────────────────
probe(
    "https://performancedata.mbta.com/lamp/tableau/rail/LAMP_static_routes.parquet",
    "LAMP Static Routes"
)

print("\n\nDone. Paste the full output back so we can build on confirmed column names.")
