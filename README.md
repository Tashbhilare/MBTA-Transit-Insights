# MBTA Performance Analyzer

A Streamlit web application for analysing Boston subway (MBTA) performance using publicly available LAMP historical data and the MBTA V3 API. Built as part of an MS Data Science project at Northeastern University, aligned with OPMI's Annual Service Delivery Report methodology.

🔗 **Live App**: [mbta-transit-insights.streamlit.app](https://mbta-transit-insights.streamlit.app)

---

## What It Does

The app has two main dashboards:

### Historical Performance
Analyses 30 days of subway performance using LAMP parquet files — the same data source OPMI uses for the Annual Service Delivery Report and MassDOT Tracker.

- On-Time Performance (OTP) trends by line
- Excess Trip Time (ETT) — primary 2024 SDP metric
- Headway Adherence — actual vs scheduled train spacing
- Peak vs Off-Peak breakdown
- Stop-level OTP to identify bottleneck stations

### Live Service Dashboard
Real-time subway monitoring using the MBTA V3 API.

- Live vehicle positions on an interactive map
- Prediction vs schedule delay distribution
- Live OTP and ETT proxy
- Active service alerts by line
- Inbound / Outbound filter per line and Green Line branch selector

---

## Data Sources

All data is publicly available. No API key required.

| Source | URL | Used For |
|--------|-----|----------|
| LAMP OTP Parquet | `performancedata.mbta.com/lamp/subway-on-time-performance-v1/` | Historical metrics |
| LAMP Static Stops | `performancedata.mbta.com/lamp/tableau/rail/LAMP_static_stops.parquet` | Station name mapping |
| LAMP Static Routes | `performancedata.mbta.com/lamp/tableau/rail/LAMP_static_routes.parquet` | Route metadata |
| MBTA V3 API — Predictions | `api-v3.mbta.com/predictions?include=schedule` | Live delay computation |
| MBTA V3 API — Vehicles | `api-v3.mbta.com/vehicles` | Live train positions |
| MBTA V3 API — Alerts | `api-v3.mbta.com/alerts` | Active service disruptions |

LAMP data has a ~2–3 day publication lag. Most recent 3 days excluded from historical analysis.

---

## Metrics

### On-Time Performance (OTP)
```
|actual_travel_time - scheduled_travel_time| ≤ 300s
```
A trip is on time if it arrives within 5 minutes of schedule. Primary metric under the 2021 Service Delivery Policy.

### Excess Trip Time (ETT)
```
max(actual - scheduled, 0) / 60
```
Extra minutes riders spend beyond the scheduled travel time. A trip is reliable if ETT ≤ 5 min. Replaced OTP as the primary subway metric in the 2024 Service Delivery Policy.

### Headway Adherence
```
actual_headway / scheduled_headway × 100%
```
How closely actual train spacing matches the schedule. Adherent if within ±25% of the scheduled gap.

### Peak / Off-Peak
- AM Peak: 6:30–9:00
- PM Peak: 15:30–18:30
- Based on `start_time` (seconds after midnight)

---

## QA / QC Notes

Several data quality issues were identified and resolved during development:

**Terminal Station Exclusion** — Ashmont, Braintree, Lake St, and Riverside appear at 0% OTP because `scheduled_travel_time` is NULL at terminals. Fixed by making `is_on_time` nullable instead of defaulting NULL to False.

**direction_id Type** — LAMP stores `direction_id` as boolean (True/False), not integer (1/0). Fixed by deriving `direction_id_int = direction_id.astype(int)`.

**service_date Parsing** — Stored as int64 (e.g. 20260304). Converted via `pd.to_datetime(service_date.astype(str), format='%Y%m%d')`.

**trunk_route_id vs route_id** — Using `route_id` splits Green Line into 4 branches (8 groups). Using `trunk_route_id` keeps 4 lines for consistent cross-line comparison.

**ETT Float Cast** — After making `is_on_time` nullable, groupby aggregations returned object dtype. Fixed by casting travel times to float before groupby.

**Headway Filter** — Only rows where both `headway_trunk_seconds` and `scheduled_headway_trunk` > 0 are used to avoid division errors.

**Validation Results:**
- Terminal stops in OTP: 0 (all excluded)
- `is_on_time` null count: 94,451
- ETT mean (31 days): 0.14 min
- Worst Red Line stop (OTP): Savin Hill 94.5%
- Failed LAMP dates: 0 of 31

---

## Project Structure
```
mbta-performance-analyzer/
├── app.py                          # Home page
├── pages/
│   ├── Historical_Analysis.py      # Historical dashboard
│   └── Live_Dashboard.py           # Live dashboard
├── utils/
│   ├── lamp.py                     # LAMP data loader
│   ├── metrics.py                  # Metric computation
│   └── api.py                      # MBTA V3 API client
├── requirements.txt
└── README.md
```

---

## Running Locally
```bash
git clone https://github.com/Tashbhilare/MBTA-Transit-Insights.git
cd MBTA-Transit-Insights
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Built With

- [Streamlit](https://streamlit.io) — web framework
- [Plotly](https://plotly.com) — interactive charts
- [Pandas](https://pandas.pydata.org) — data processing
- [PyArrow](https://arrow.apache.org/docs/python/) — parquet file reading
- [LAMP](https://performancedata.mbta.com) — historical data
- [MBTA V3 API](https://api-v3.mbta.com) — live data

---

## Author

**Tanish Bhilare**
MS Data Science, Northeastern University

- GitHub: [@Tashbhilare](https://github.com/Tashbhilare)
- LinkedIn: [tanishdhongade](https://linkedin.com/in/tanishdhongade)
