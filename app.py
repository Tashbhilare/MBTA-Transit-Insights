"""
app.py — MBTA Performance Analyzer home page.
"""
import sys
import base64
sys.path.insert(0, '.')
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="MBTA Performance Analyzer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom T favicon ──────────────────────────────────────────────────────────
favicon_svg = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="48" fill="#066ab5" stroke="#066ab5" stroke-width="2"/>
  <rect x="25" y="22" width="50" height="12" fill="white"/>
  <rect x="43" y="22" width="14" height="56" fill="white"/>
</svg>
"""
b64 = base64.b64encode(favicon_svg.encode()).decode()
st.markdown(
    f'<link rel="shortcut icon" href="data:image/svg+xml;base64,{b64}">',
    unsafe_allow_html=True
)

st.markdown("""
<style>
header, footer, #MainMenu,
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
[data-testid="stDeployButton"]    { display: none !important; }

.main .block-container            { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewBlockContainer"] { padding: 0 !important; }
html, body                        { margin: 0 !important; padding: 0 !important; }
.stApp                            { margin: 0 !important; padding: 0 !important; }
div[data-testid="stVerticalBlock"] { gap: 0 !important; }

* { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important; }

:root { --navy: #066ab5; }

iframe {
    display: block !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    width: 100% !important;
}

.content { padding: 24px 40px 0; }
.divider { border: none; border-top: 1px solid #e9ecef; margin: 10px 0; }

.nav-card {
    border: 1px solid #dee2e6; border-radius: 8px;
    padding: 28px 28px 24px; background: #fff;
    display: block; transition: box-shadow 0.15s, border-color 0.15s;
    min-height: 300px;
}
.nav-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.09); border-color: var(--navy); }
.nav-card-blue { border-top: 5px solid var(--navy); }

.nav-card-title {
    font-size: 18px !important; font-weight: 700;
    color: #1a1a1a !important; margin: 0 0 10px;
}
.nav-card-desc {
    font-size: 14px !important; color: #555 !important;
    line-height: 1.65; margin: 0 0 18px;
}
.nav-card-meta { list-style: none; padding: 0; margin: 0 0 20px; }
.nav-card-meta li {
    font-size: 14px !important; color: #555 !important;
    padding: 5px 0; border-bottom: 1px solid #f1f3f5;
    display: flex; align-items: center; gap: 8px;
}
.nav-card-meta li:last-child { border-bottom: none; }
.nav-card-meta li::before {
    content: ""; width: 6px; height: 6px; border-radius: 50%;
    background: var(--navy); flex-shrink: 0;
}
.nav-card-link {
    font-size: 12px !important; font-weight: 800;
    color: var(--navy) !important; letter-spacing: 0.05em; text-transform: uppercase;
}
a .nav-card-title  { color: #1a1a1a !important; }
a .nav-card-desc   { color: #555 !important; }
a .nav-card-meta li { color: #555 !important; }
a .nav-card-link   { color: var(--navy) !important; }
a:link, a:visited  { color: inherit; }

.section-label {
    font-size: 11px !important; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.12em; color: #aaa;
    padding-bottom: 6px; border-bottom: 1px solid #e9ecef; margin: 0 0 16px;
}

.metrics-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 12px; margin-bottom: 10px;
}
.metric-card {
    background: #fff; border-radius: 6px;
    padding: 16px 18px; border: 1px solid #e9ecef;
    border-left: 4px solid var(--navy);
}
.metric-card-title {
    font-size: 18px !important; font-weight: 700;
    color: #1a1a1a !important; margin: 0 0 8px;
}
.metric-card-formula {
    font-size: 13px !important; color: #495057 !important; margin: 0 0 8px;
    background: #f8f9fa; padding: 5px 10px; border-radius: 4px;
    font-family: monospace !important; display: inline-block;
}
.metric-card-desc {
    font-size: 14px !important; color: #555 !important;
    margin: 8px 0 0; line-height: 1.6;
}
.metric-card-policy {
    font-size: 12px !important; color: #adb5bd !important;
    margin: 6px 0 0; font-style: italic;
}

.footer {
    border-top: 1px solid #e9ecef; padding: 12px 0 16px;
    text-align: center; font-size: 12px !important; color: #bbb;
}
.footer a { color: #bbb; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ── Header + Modal ────────────────────────────────────────────────────────────
components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
* { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; background: #066ab5; }

.mbta-header {
    background: #066ab5;
    padding: 12px 40px 10px;
    width: 100%;
}
.mbta-title-row {
    display: flex; align-items: center;
    justify-content: space-between; padding-bottom: 4px;
}
.mbta-title { font-size: 18px; font-weight: 700; color: #fff; margin: 0; }
.mbta-sub   { font-size: 12px; color: rgba(255,255,255,0.65); margin: 2px 0 0; }

.mbta-nav { display: flex; align-items: center; gap: 6px; padding-top: 0; }
.mbta-nav a {
    background: rgba(255,255,255,0.12); color: #fff;
    border: 1px solid rgba(255,255,255,0.3); border-radius: 4px;
    font-size: 12px; font-weight: 600; padding: 5px 16px;
    text-decoration: none; text-transform: uppercase;
    letter-spacing: 0.04em; white-space: nowrap; cursor: pointer;
    transition: background 0.15s;
}
.mbta-nav a:hover, .mbta-nav a.active { background: rgba(255,255,255,0.28); }
</style>

<script>
function goHome() {
    window.parent.location.href = window.parent.location.origin;
}

function openModal() {
    var parent = window.parent.document;
    var existing = parent.getElementById('dataModalParent');
    if (existing) existing.remove();

    var modal = parent.createElement('div');
    modal.id = 'dataModalParent';
    modal.innerHTML = `
    <div onclick="if(event.target===this){this.parentElement.remove()}"
         style="position:fixed;top:0;left:0;width:100%;height:100%;
                background:rgba(0,0,0,0.45);z-index:99999;
                display:flex;align-items:center;justify-content:center;
                font-family:Helvetica Neue,Helvetica,Arial,sans-serif;">
        <div style="background:#fff;border-radius:10px;padding:36px 40px;
                    max-width:680px;width:90%;position:relative;
                    max-height:80vh;overflow-y:auto;
                    box-shadow:0 8px 40px rgba(0,0,0,0.18);">

            <span onclick="document.getElementById('dataModalParent').remove()"
                  style="position:absolute;top:14px;right:18px;font-size:22px;
                         color:#adb5bd;cursor:pointer;font-weight:700;line-height:1;">
                &times;
            </span>

            <p style="font-size:18px;font-weight:700;color:#1a1a1a;margin:0 0 4px;">
                Data Sources
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 20px;">
                All data used in this project is publicly available.
                No API key required for any source.
            </p>
            <hr style="border:none;border-top:1px solid #e9ecef;margin:0 0 20px;">

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                LAMP — Subway On-Time Performance
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    performancedata.mbta.com/lamp/subway-on-time-performance-v1/
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
                One parquet file per service date. Each row is a trip &times; stop pair
                containing actual travel time, scheduled travel time, headway measurements,
                direction, and station ID. Same dataset OPMI loads into Tableau for the
                Annual Service Delivery Report. 1,218,114 rows across 31 service dates
                (Feb&ndash;Mar 2026).
            </p>

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                LAMP — Static Stops
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    performancedata.mbta.com/lamp/tableau/rail/LAMP_static_stops.parquet
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
                Station names, parent station IDs, and coordinates. Used to map place codes
                (e.g. place-harsq) to readable names (e.g. Harvard) in stop-level charts.
            </p>

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                LAMP — Static Routes
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    performancedata.mbta.com/lamp/tableau/rail/LAMP_static_routes.parquet
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
                Route metadata used for line-level grouping and filtering by
                trunk_route_id (Red, Orange, Green, Blue).
            </p>

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                MBTA V3 API — Live Predictions
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    api-v3.mbta.com/predictions?include=schedule
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
                Real-time predictions with scheduled times. Used to compute live delay
                (predicted &minus; scheduled). No API key required.
                Rate limited to 20 req/min unauthenticated.
            </p>

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                MBTA V3 API — Vehicle Positions
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    api-v3.mbta.com/vehicles
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
                Live train positions, current status (Stopped At, In Transit To, Incoming At),
                and speed. Displayed on the vehicle map in the Live Dashboard.
            </p>

            <p style="font-size:14px;font-weight:700;color:#1a1a1a;margin:0 0 2px;">
                MBTA V3 API — Service Alerts
            </p>
            <p style="font-size:12px;color:#495057;margin:0 0 4px;">
                <code style="background:#f8f9fa;padding:2px 6px;border-radius:3px;">
                    api-v3.mbta.com/alerts
                </code>
            </p>
            <p style="font-size:14px;color:#555;margin:0 0 8px;line-height:1.6;">
                Active service disruptions including effect, severity, and header text.
                Displayed in the Alerts tab of the Live Dashboard.
            </p>

            <hr style="border:none;border-top:1px solid #e9ecef;margin:16px 0 12px;">
            <p style="font-size:12px;color:#adb5bd;margin:0;">
                All sources are public and free. LAMP has a ~2&ndash;3 day lag.
                Most recent 3 days excluded from historical analysis.
            </p>
        </div>
    </div>`;
    parent.body.appendChild(modal);
}
</script>
</head>
<body>

<div class="mbta-header">
    <div class="mbta-title-row">
        <div>
            <div class="mbta-title">MBTA Performance Analyzer</div>
            <div class="mbta-sub">
                LAMP Historical Data &nbsp;·&nbsp; MBTA V3 API &nbsp;·&nbsp; OPMI Aligned
            </div>
        </div>
        <nav class="mbta-nav">
            <a onclick="goHome()" class="active">Home</a>
            <a onclick="openModal()">Data</a>
        </nav>
    </div>
</div>

</body>
</html>
""", height=90, scrolling=False)

# ── Content ───────────────────────────────────────────────────────────────────
st.markdown("<div class='content'><hr class='divider'>", unsafe_allow_html=True)

# ── Nav cards ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2, gap="large")

with c1:
    st.markdown(
        "<a href='/Historical_Analysis' target='_self' style='text-decoration:none;display:block;'>"
        "<div class='nav-card nav-card-blue'>"
        "<p class='nav-card-title'>Historical Performance</p>"
        "<p class='nav-card-desc'>Analyse 30 days of subway performance using LAMP parquet data "
        "— the same source OPMI uses for the Annual Service Delivery Report and MassDOT Tracker. "
        "Filter by line and explore trends over time.</p>"
        "<ul class='nav-card-meta'>"
        "<li>On-Time Performance (OTP) — % of trips within &plusmn;5 min of schedule</li>"
        "<li>Excess Trip Time (ETT) — average extra minutes per trip, 2024 SDP metric</li>"
        "<li>Headway Adherence — actual vs scheduled train spacing</li>"
        "<li>Peak vs Off-Peak breakdown per line</li>"
        "<li>Stop-level OTP to identify bottleneck stations</li>"
        "</ul>"
        "<span class='nav-card-link'>Explore Trends &rarr;</span>"
        "</div></a>",
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        "<a href='/Live_Dashboard' target='_self' style='text-decoration:none;display:block;'>"
        "<div class='nav-card nav-card-blue'>"
        "<p class='nav-card-title'>Live Service Dashboard</p>"
        "<p class='nav-card-desc'>Monitor subway service in real time using the MBTA V3 API. "
        "Live predictions are compared against scheduled departures to compute delay. "
        "Data refreshes on every page load.</p>"
        "<ul class='nav-card-meta'>"
        "<li>Live vehicle positions on an interactive map</li>"
        "<li>Delay distribution — prediction vs scheduled departure</li>"
        "<li>Live OTP and ETT proxy computed from current predictions</li>"
        "<li>Active service alerts by line</li>"
        "<li>Inbound / Outbound direction filter per line</li>"
        "</ul>"
        "<span class='nav-card-link'>View Live Map &rarr;</span>"
        "</div></a>",
        unsafe_allow_html=True
    )

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────────────────────
st.markdown("<p class='section-label'>How Metrics Are Calculated</p>", unsafe_allow_html=True)

metrics = [
    {
        "title":   "On-Time Performance (OTP)",
        "formula": "|actual_tt &minus; scheduled_tt| &le; 300s",
        "desc":    "A trip is on time if it arrives within 5 minutes of its scheduled travel time. Expressed as a percentage of all trips.",
        "policy":  "2021 Service Delivery Policy",
    },
    {
        "title":   "Excess Trip Time (ETT)",
        "formula": "max(actual &minus; scheduled, 0) &divide; 60",
        "desc":    "Extra minutes riders spend beyond the scheduled travel time. A trip is reliable if ETT &le; 5 min. Replaced OTP as the primary subway metric in 2024.",
        "policy":  "2024 Service Delivery Policy &middot; primary subway metric",
    },
    {
        "title":   "Headway Adherence",
        "formula": "actual_hw &divide; scheduled_hw &times; 100%",
        "desc":    "How closely actual train spacing matches the schedule. Adherent if within &plusmn;25% of the scheduled gap. For frequent service, spacing matters more than schedule lookup.",
        "policy":  "MBTA Annual Service Delivery Report",
    },
    {
        "title":   "Peak / Off-Peak Split",
        "formula": "AM 6:30&ndash;9:00 &nbsp;|&nbsp; PM 15:30&ndash;18:30",
        "desc":    "Trips classified by start_time (seconds after midnight). Peak periods reflect higher demand and typically see worse performance.",
        "policy":  "2024 SDP period definitions",
    },
    {
        "title":   "Stop-Level OTP",
        "formula": "OTP grouped by parent_station",
        "desc":    "OTP broken down by station to identify which stops cause the most delays. Terminal stops excluded where scheduled_travel_time is null.",
        "policy":  "OPMI Annual SDR methodology",
    },
    {
        "title":   "Live Delay (V3 API)",
        "formula": "predicted_departure &minus; scheduled_departure",
        "desc":    "Real-time delay from the MBTA V3 API comparing live predictions against scheduled departures. Positive = running late.",
        "policy":  "MBTA V3 API &middot; /predictions?include=schedule",
    },
]

cards_html = "<div class='metrics-grid'>"
for m in metrics:
    cards_html += (
        "<div class='metric-card'>"
        f"<p class='metric-card-title'>{m['title']}</p>"
        f"<p class='metric-card-formula'>{m['formula']}</p>"
        f"<p class='metric-card-desc'>{m['desc']}</p>"
        f"<p class='metric-card-policy'>{m['policy']}</p>"
        "</div>"
    )
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>"
    "Built by Tanish Bhilare &nbsp;·&nbsp; MS Data Science, Northeastern University &nbsp;·&nbsp;"
    "<a href='https://github.com/Tashbhilare'>GitHub</a> &nbsp;·&nbsp;"
    "<a href='https://linkedin.com/in/tanishdhongade'>LinkedIn</a>"
    "</div></div>",
    unsafe_allow_html=True
)