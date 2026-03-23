"""
pages/Live_Dashboard.py
Real-time MBTA performance using V3 API.
"""

import sys
sys.path.insert(0, '.')

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz

from utils.api import (
    get_vehicles, get_predictions, get_alerts,
    compute_live_metrics, ROUTE_OPTIONS, LINE_COLORS,
)

st.set_page_config(
    page_title="Live Dashboard — MBTA",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Time ──────────────────────────────────────────────────────────────────────
est = pytz.timezone("America/New_York")
now = datetime.now(est).strftime("%I:%M %p ET")

st.markdown("""
<style>
header, footer, #MainMenu,
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
[data-testid="stDeployButton"] { display: none !important; }

.main .block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewBlockContainer"] { padding: 0 !important; }
html, body { margin: 0 !important; padding: 0 !important; }
.stApp     { margin: 0 !important; padding: 0 !important; }
div[data-testid="stVerticalBlock"] { gap: 0 !important; }

* { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important; }

.mbta-header {
    background: #066ab5;
    padding: 12px 48px 0px;
    width: 100%; box-sizing: border-box;
}
.mbta-title-row {
    display: flex; align-items: flex-start;
    justify-content: space-between; padding-bottom: 10px;
}
.mbta-header-title { color: #fff; font-size: 1.2rem; font-weight: 700; margin: 0; }
.mbta-header-sub   { color: rgba(255,255,255,0.65); font-size: 0.72rem; margin: 2px 0 0; }

.mbta-nav { display: flex; align-items: center; gap: 6px; padding-top: 4px; }
.mbta-nav a {
    background: rgba(255,255,255,0.12); color: #fff !important;
    border: 1px solid rgba(255,255,255,0.3); border-radius: 4px;
    font-size: 0.72rem; font-weight: 600; padding: 5px 16px;
    text-decoration: none !important; text-transform: uppercase;
    letter-spacing: 0.04em; white-space: nowrap; transition: background 0.15s;
}
.mbta-nav a:hover { background: rgba(255,255,255,0.28); }

.line-selector {
    display: flex; gap: 10px; padding: 14px 48px; flex-wrap: wrap;
    background: #f8f9fa; border-bottom: 1px solid #e9ecef;
    align-items: center;
}
.line-btn {
    display: inline-flex; align-items: center; gap: 10px;
    padding: 7px 18px 7px 7px; border-radius: 40px;
    border: 2px solid #dee2e6; background: #fff;
    cursor: pointer; text-decoration: none !important;
    transition: all 0.15s; font-size: 0.85rem; font-weight: 600;
    color: #333 !important;
}
.line-btn:hover { border-color: #aaa; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.line-btn .circle {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.65rem; font-weight: 800; color: #fff;
    letter-spacing: 0.02em; flex-shrink: 0;
}
.line-btn.active-all    { background: #495057; border-color: #495057; color: #fff !important; }
.line-btn.active-red    { background: #DA291C; border-color: #DA291C; color: #fff !important; }
.line-btn.active-orange { background: #ED8B00; border-color: #ED8B00; color: #fff !important; }
.line-btn.active-green  { background: #00843D; border-color: #00843D; color: #fff !important; }
.line-btn.active-blue   { background: #003A9B; border-color: #003A9B; color: #fff !important; }

.green-dropdown {
    display: none; position: absolute; top: 100%; left: 0;
    background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12); z-index: 999;
    min-width: 160px; padding: 4px 0; margin-top: 4px;
}
div:hover > .green-dropdown { display: block; }
.green-dropdown a:hover { background: rgba(0,132,61,0.08) !important; }

.content { padding: 20px 48px 0; }
.divider { border: none; border-top: 1px solid #e9ecef; margin: 16px 0; }

.metric-block { padding: 0 0 8px; }
.metric-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #6c757d; margin: 0 0 5px;
}
.metric-value { font-size: 2rem; font-weight: 700; color: #212529; line-height: 1.1; margin: 0; }
.metric-context { font-size: 0.73rem; color: #6c757d; margin: 4px 0 0; }

.section-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: #6c757d;
    padding-bottom: 8px; border-bottom: 1px solid #e9ecef; margin: 0 0 16px;
}

.alert-card {
    border-left: 4px solid #DA291C; padding: 10px 16px;
    background: #fff8f8; border-radius: 6px; margin-bottom: 10px;
}
.alert-card.warning { border-left-color: #ED8B00; background: #fffbf0; }
.alert-effect   { font-size: 0.82rem; font-weight: 700; color: #212529; }
.alert-severity { font-size: 0.72rem; color: #6c757d; margin-left: 8px; }
.alert-header   { font-size: 0.85rem; color: #333; margin: 4px 0; }
.alert-updated  { font-size: 0.72rem; color: #adb5bd; }
</style>
""", unsafe_allow_html=True)

# ── Line config ───────────────────────────────────────────────────────────────
LINE_CONFIG = {
    "All":     {"badge": "ALL", "color": "#495057", "name": "All Lines",    "active_class": "active-all"},
    "Red":     {"badge": "RL",  "color": "#DA291C", "name": "Red Line",     "active_class": "active-red"},
    "Orange":  {"badge": "OL",  "color": "#ED8B00", "name": "Orange Line",  "active_class": "active-orange"},
    "Green":   {"badge": "GL",  "color": "#00843D", "name": "Green Line",   "active_class": "active-green"},
    "Green-B": {"badge": "B",   "color": "#00843D", "name": "Green Line B", "active_class": "active-green"},
    "Green-C": {"badge": "C",   "color": "#00843D", "name": "Green Line C", "active_class": "active-green"},
    "Green-D": {"badge": "D",   "color": "#00843D", "name": "Green Line D", "active_class": "active-green"},
    "Green-E": {"badge": "E",   "color": "#00843D", "name": "Green Line E", "active_class": "active-green"},
    "Blue":    {"badge": "BL",  "color": "#003A9B", "name": "Blue Line",    "active_class": "active-blue"},
}

GREEN_SUBS = ["Green-B", "Green-C", "Green-D", "Green-E"]
TOP_LINES  = ["All", "Red", "Orange", "Green", "Blue"]

# ── Read query params ─────────────────────────────────────────────────────────
if st.query_params.get("refresh") == "1":
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

line_param = st.query_params.get("line", "All")
if line_param not in LINE_CONFIG:
    line_param = "All"
sel = line_param

dir_param    = st.query_params.get("dir", "1")
direction_id = int(dir_param) if dir_param in ("0", "1") else 1

sel_cfg    = LINE_CONFIG[sel]
line_color = sel_cfg["color"]

# ── Build badges HTML ─────────────────────────────────────────────────────────
badges_html = ""
for key in TOP_LINES:
    cfg       = LINE_CONFIG[key]
    is_active = sel == key

    if key == "Green":
        green_sub_active = sel in GREEN_SUBS
        is_green_active  = is_active or green_sub_active
        green_btn_class  = "line-btn active-green" if is_green_active else "line-btn"
        green_text       = "#fff" if is_green_active else "#333"
        green_circle_bg  = "#fff" if is_green_active else "#00843D"
        green_circle_fg  = "#00843D" if is_green_active else "#fff"

        sub_items = ""
        for sub in GREEN_SUBS:
            sub_cfg    = LINE_CONFIG[sub]
            sub_active = sel == sub
            sub_bg     = "rgba(0,132,61,0.12)" if sub_active else "transparent"
            sub_weight = "700" if sub_active else "500"
            sub_items += (
                f"<a href='?line={sub}&dir={direction_id}' target='_self' "
                f"style='display:flex; align-items:center; gap:8px; padding:7px 14px; "
                f"text-decoration:none; background:{sub_bg}; font-weight:{sub_weight}; "
                f"color:#1a1a1a; font-size:0.82rem; white-space:nowrap;'>"
                f"<span style='background:#00843D; color:#fff; width:22px; height:22px; "
                f"border-radius:50%; display:flex; align-items:center; justify-content:center; "
                f"font-size:0.62rem; font-weight:800; flex-shrink:0;'>{sub_cfg['badge']}</span>"
                f"{sub_cfg['name']}</a>"
            )

        badges_html += (
            f"<div style='position:relative; display:inline-block;'>"
            f"<a href='?line=Green&dir={direction_id}' target='_self' "
            f"class='{green_btn_class}' style='color:{green_text} !important;'>"
            f"<span class='circle' style='background:{green_circle_bg}; "
            f"color:{green_circle_fg}; font-size:0.65rem;'>GL</span>"
            f"Green Line"
            f"<span style='font-size:0.65rem; margin-left:2px; opacity:0.7;'>&#9660;</span>"
            f"</a>"
            f"<div class='green-dropdown'>{sub_items}</div>"
            f"</div>"
        )
    else:
        if key == "All":
            circle_bg = "#fff" if is_active else "#495057"
            circle_fg = "#495057" if is_active else "#fff"
        else:
            circle_bg = "#fff" if is_active else cfg["color"]
            circle_fg = cfg["color"] if is_active else "#fff"
        text_color = "#fff" if is_active else "#333"
        font_size  = "0.6rem" if key == "All" else "0.65rem"
        base_class = f"line-btn {cfg['active_class']}" if is_active else "line-btn"

        badges_html += (
            f"<a href='?line={key}&dir={direction_id}' target='_self' "
            f"class='{base_class}' style='color:{text_color} !important;'>"
            f"<span class='circle' style='background:{circle_bg}; color:{circle_fg}; "
            f"font-size:{font_size};'>{cfg['badge']}</span>"
            f"{cfg['name']}</a>"
        )

# ── Direction + Refresh controls ──────────────────────────────────────────────
dir_0_bg     = "#066ab5" if direction_id == 0 else "#fff"
dir_0_color  = "#fff"    if direction_id == 0 else "#6c757d"
dir_0_border = "#066ab5" if direction_id == 0 else "#dee2e6"
dir_1_bg     = "#066ab5" if direction_id == 1 else "#fff"
dir_1_color  = "#fff"    if direction_id == 1 else "#6c757d"
dir_1_border = "#066ab5" if direction_id == 1 else "#dee2e6"

controls_html = (
    "<div style='margin-left:auto; display:flex; align-items:center; gap:8px;'>"
    f"<a href='?line={sel}&dir=0' target='_self' "
    f"style='display:inline-flex; align-items:center; padding:7px 16px; "
    f"border-radius:40px; border:2px solid {dir_0_border}; background:{dir_0_bg}; "
    f"font-size:0.85rem; font-weight:600; color:{dir_0_color} !important; "
    f"text-decoration:none;'>Outbound</a>"
    f"<a href='?line={sel}&dir=1' target='_self' "
    f"style='display:inline-flex; align-items:center; padding:7px 16px; "
    f"border-radius:40px; border:2px solid {dir_1_border}; background:{dir_1_bg}; "
    f"font-size:0.85rem; font-weight:600; color:{dir_1_color} !important; "
    f"text-decoration:none;'>Inbound</a>"
    f"<a href='?line={sel}&dir={direction_id}&refresh=1' target='_self' "
    f"style='display:inline-flex; align-items:center; padding:7px 16px; "
    f"border-radius:40px; border:2px solid #dee2e6; background:#fff; "
    f"font-size:0.85rem; font-weight:600; color:#333 !important; "
    f"text-decoration:none;'>Refresh</a>"
    "</div>"
)

# ── Header HTML ───────────────────────────────────────────────────────────────
header_html = (
    "<div class='mbta-header'>"
    "<div class='mbta-title-row'>"
    "<div>"
    "<div class='mbta-header-title'>MBTA Performance Analyzer</div>"
    f"<div class='mbta-header-sub'>Live Service Dashboard &nbsp;·&nbsp; MBTA V3 API"
    f" &nbsp;·&nbsp; {now} &nbsp;·&nbsp; Refreshes on page load</div>"
    "</div>"
    "<nav class='mbta-nav'>"
    "<a href='/' target='_self'>Home</a>"
    "</nav>"
    "</div>"
    "</div>"
    f"<div class='line-selector'>{badges_html}{controls_html}</div>"
)

st.markdown(header_html, unsafe_allow_html=True)

# ── Resolve route_id for API ──────────────────────────────────────────────────
ROUTE_KEY_MAP = {
    "All":     "Red Line",
    "Red":     "Red Line",
    "Orange":  "Orange Line",
    "Green":   "Green Line",
    "Green-B": "Green-B",
    "Green-C": "Green-C",
    "Green-D": "Green-D",
    "Green-E": "Green-E",
    "Blue":    "Blue Line",
}
route_key = ROUTE_KEY_MAP.get(sel, "Red Line")
route_id  = ROUTE_OPTIONS.get(route_key, list(ROUTE_OPTIONS.values())[0])
sel_label = LINE_CONFIG[sel]["name"]

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_live(route_id, direction_id):
    vehicles = get_vehicles(route_id, direction_id)
    preds    = get_predictions(route_id, direction_id)
    alerts   = get_alerts(route_id)
    return vehicles, preds, alerts

with st.spinner("Fetching live data..."):
    try:
        vehicles_df, preds_df, alerts = load_live(route_id, direction_id)
        data_ok = True
    except Exception as e:
        st.error(f"API error: {e}")
        data_ok = False

if not data_ok:
    st.stop()

live = compute_live_metrics(preds_df)

# ── Content ───────────────────────────────────────────────────────────────────
st.markdown("<div class='content'>", unsafe_allow_html=True)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown("<p class='section-label'>Live Snapshot</p>", unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    dir_label = "Inbound" if direction_id == 1 else "Outbound"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>Active Trains</p>
        <p class='metric-value'>{len(vehicles_df)}</p>
        <p class='metric-context'>{sel_label} · {dir_label}</p>
    </div>""", unsafe_allow_html=True)

with k2:
    otp_val = f"{live['otp_pct']}%" if live['otp_pct'] is not None else "—"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>Live OTP</p>
        <p class='metric-value' style='color:{line_color};'>{otp_val}</p>
        <p class='metric-context'>Within ±5 min of schedule</p>
    </div>""", unsafe_allow_html=True)

with k3:
    delay_val = f"{live['avg_delay_min']} min" if live['avg_delay_min'] is not None else "—"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>Avg Delay</p>
        <p class='metric-value' style='color:{line_color};'>{delay_val}</p>
        <p class='metric-context'>Predicted vs scheduled departure</p>
    </div>""", unsafe_allow_html=True)

with k4:
    ett_val  = f"{live['ett_min']} min" if live['ett_min'] is not None else "—"
    ett_ok   = live['ett_min'] is not None and live['ett_min'] <= 5
    ett_note = "On target (≤ 5 min)" if ett_ok else "Above threshold"
    ett_col  = "#00843D" if ett_ok else "#DA291C"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>ETT Proxy</p>
        <p class='metric-value' style='color:{line_color};'>{ett_val}</p>
        <p class='metric-context' style='color:{ett_col};'>{ett_note}</p>
    </div>""", unsafe_allow_html=True)

with k5:
    alert_note = "Active disruptions" if alerts else "No active alerts"
    alert_col  = "#DA291C" if alerts else "#00843D"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>Active Alerts</p>
        <p class='metric-value'>{len(alerts)}</p>
        <p class='metric-context' style='color:{alert_col};'>{alert_note}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

CHART_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=30, l=10, r=10),
    font=dict(family="sans-serif", size=11, color="#495057"),
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Vehicle Map", "Delay Distribution", "Alerts"])

# ── Tab 1: Map + Vehicle Status side by side ──────────────────────────────────
with tab1:
    has_coords = "latitude" in vehicles_df.columns and "longitude" in vehicles_df.columns
    map_df = vehicles_df.dropna(subset=["latitude", "longitude"]) if has_coords else vehicles_df.iloc[0:0]

    if not map_df.empty and has_coords:
        map_col, table_col = st.columns([3, 2], gap="large")

        with map_col:
            st.markdown("<p class='section-label'>Live Vehicle Positions</p>",
                        unsafe_allow_html=True)
            fig = px.scatter_mapbox(
                map_df,
                lat="latitude", lon="longitude",
                hover_name="label",
                hover_data={
                    "latitude": False, "longitude": False,
                    "current_status": True, "speed_mph": True,
                },
                color_discrete_sequence=[line_color],
                zoom=11, height=460,
            )
            fig.update_traces(marker=dict(size=14))
            fig.update_layout(
                mapbox_style="carto-positron",
                margin=dict(l=0, r=0, t=0, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        with table_col:
            st.markdown("<p class='section-label'>Vehicle Status</p>",
                        unsafe_allow_html=True)
            display_cols = [c for c in ["label", "current_status", "speed_mph"]
                            if c in vehicles_df.columns]
            st.dataframe(
                vehicles_df[display_cols].rename(columns={
                    "label": "Train", "current_status": "Status",
                    "speed_mph": "Speed (mph)"}),
                use_container_width=True,
                height=460,
            )
    else:
        st.info("No active vehicles reporting position right now.")

# ── Tab 2: Delay Distribution + Stop-Level side by side ───────────────────────
with tab2:
    has_delay = not preds_df.empty and "delay_min" in preds_df.columns
    if has_delay:
        delays = preds_df["delay_min"].dropna()
        if not delays.empty:
            dist_col, stop_col = st.columns(2, gap="large")

            with dist_col:
                st.markdown("<p class='section-label'>Prediction vs Schedule — Delay Distribution</p>",
                            unsafe_allow_html=True)
                fig2 = px.histogram(
                    delays, nbins=30,
                    labels={"value": "Delay (min)", "count": "Trips"},
                    color_discrete_sequence=[line_color],
                    height=300,
                )
                fig2.add_vline(x=0,  line_dash="dash", line_color="#adb5bd",
                               annotation_text="On time")
                fig2.add_vline(x=5,  line_dash="dot",  line_color="#DA291C",
                               annotation_text="+5 min")
                fig2.add_vline(x=-5, line_dash="dot",  line_color="#DA291C",
                               annotation_text="−5 min")
                fig2.update_layout(showlegend=False, **CHART_BASE)
                st.plotly_chart(fig2, use_container_width=True)

                total = len(delays)
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown(f"""
                    <div class='metric-block'>
                        <p class='metric-label'>On Time (±5 min)</p>
                        <p class='metric-value' style='color:#00843D;'>{live['otp_pct']}%</p>
                        <p class='metric-context'>{live['on_time']} trips</p>
                    </div>""", unsafe_allow_html=True)
                with m2:
                    st.markdown(f"""
                    <div class='metric-block'>
                        <p class='metric-label'>Late (&gt;5 min)</p>
                        <p class='metric-value' style='color:#DA291C;'>{live['late']/total*100:.0f}%</p>
                        <p class='metric-context'>{live['late']} trips</p>
                    </div>""", unsafe_allow_html=True)
                with m3:
                    st.markdown(f"""
                    <div class='metric-block'>
                        <p class='metric-label'>Early (&gt;5 min)</p>
                        <p class='metric-value' style='color:#ED8B00;'>{live['early']/total*100:.0f}%</p>
                        <p class='metric-context'>{live['early']} trips</p>
                    </div>""", unsafe_allow_html=True)

            with stop_col:
                st.markdown("<p class='section-label'>Stop-Level Predictions</p>",
                            unsafe_allow_html=True)
                display_cols = [c for c in ["stop_name", "delay_min", "status"]
                                if c in preds_df.columns]
                st.dataframe(
                    preds_df[display_cols].rename(columns={
                        "stop_name": "Stop", "delay_min": "Delay (min)",
                        "status": "Status"}).head(30),
                    use_container_width=True,
                    height=380,
                )
        else:
            st.info("No delay data available right now.")
    else:
        st.info("No live prediction data available right now.")

# ── Tab 3: Alerts ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown("<p class='section-label'>Active Service Alerts</p>", unsafe_allow_html=True)
    if alerts:
        for a in alerts:
            is_severe  = a["severity"] in ("Severe", "High")
            card_class = "alert-card" if is_severe else "alert-card warning"
            st.markdown(f"""
            <div class='{card_class}'>
                <span class='alert-effect'>{a['effect']}</span>
                <span class='alert-severity'>Severity: {a['severity']}</span>
                <p class='alert-header'>{a['header']}</p>
                <p class='alert-updated'>Updated: {a['updated_at']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active service alerts for this line.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("""
<p style='font-size:0.72rem;color:#adb5bd;text-align:center;padding-bottom:24px;'>
    Built by Tanish Bhilare &nbsp;·&nbsp; MS Data Science, Northeastern University &nbsp;·&nbsp;
    Data: MBTA V3 API &nbsp;·&nbsp;
    <a href='https://github.com/Tashbhilare' style='color:#adb5bd;'>GitHub</a> &nbsp;·&nbsp;
    <a href='https://linkedin.com/in/tanishdhongade' style='color:#adb5bd;'>LinkedIn</a>
</p>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)