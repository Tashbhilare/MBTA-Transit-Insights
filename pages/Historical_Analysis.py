"""
pages/Historical_Analysis.py
MBTA Performance Analyzer — Historical Analysis.
"""

import sys
sys.path.insert(0, '.')

import streamlit as st
import plotly.graph_objects as go

from utils.lamp import load_lamp_days, load_static_stops, SUBWAY_LINES
from utils.metrics import (
    otp_by_line, otp_trend,
    ett_by_line, ett_trend,
    headway_by_line, headway_by_stop,
    otp_by_stop, kpi_snapshot,
    ETT_THRESHOLD_MIN,
)

st.set_page_config(
    page_title="MBTA Performance Analyzer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
    display: flex; gap: 10px; padding: 14px 48px 14px; flex-wrap: wrap;
    background: #f8f9fa; border-bottom: 1px solid #e9ecef;
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
</style>
""", unsafe_allow_html=True)

# ── Load LAMP data ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load(days):
    return load_lamp_days(days_back=days)

# ── Load stop name mapping from LAMP static stops ─────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def load_stop_names():
    try:
        stops = load_static_stops()
        if "parent_station" in stops.columns and "stop_name" in stops.columns:
            m = stops.dropna(subset=["parent_station", "stop_name"])
            m = m.drop_duplicates(subset=["parent_station"])
            return dict(zip(m["parent_station"], m["stop_name"]))
        elif "stop_id" in stops.columns and "stop_name" in stops.columns:
            return dict(zip(stops["stop_id"], stops["stop_name"]))
    except Exception:
        pass
    return {}

with st.spinner("Loading LAMP data..."):
    try:
        raw = load(30)
        data_ok = True
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        data_ok = False

if not data_ok:
    st.stop()

STOP_NAME_MAP = load_stop_names()

def clean_stop_name(code):
    if code in STOP_NAME_MAP:
        return STOP_NAME_MAP[code]
    return code.replace("place-", "").replace("-", " ").title()

# ── Line config ───────────────────────────────────────────────────────────────
LINE_CONFIG = {
    "Red":    {"badge": "RL", "color": "#DA291C", "name": "Red Line",    "active_class": "active-red"},
    "Orange": {"badge": "OL", "color": "#ED8B00", "name": "Orange Line", "active_class": "active-orange"},
    "Green":  {"badge": "GL", "color": "#00843D", "name": "Green Line",  "active_class": "active-green"},
    "Blue":   {"badge": "BL", "color": "#003A9B", "name": "Blue Line",   "active_class": "active-blue"},
}

MUTED = {
    "Red":    "rgba(218,41,28,0.15)",
    "Orange": "rgba(237,139,0,0.15)",
    "Green":  "rgba(0,132,61,0.15)",
    "Blue":   "rgba(0,58,155,0.15)",
}

CHART_BASE = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=30, l=10, r=10),
    font=dict(family="sans-serif", size=11, color="#495057"),
)

def bar_colors(lines, selected):
    if selected == "All":
        return [LINE_CONFIG[l]["color"] for l in lines]
    return [
        LINE_CONFIG[l]["color"] if l == selected
        else MUTED.get(l, "rgba(136,136,136,0.15)")
        for l in lines
    ]

# ── Session state ─────────────────────────────────────────────────────────────
line_param = st.query_params.get("line", "All")
if line_param in LINE_CONFIG or line_param == "All":
    st.session_state.sel = line_param
elif "sel" not in st.session_state:
    st.session_state.sel = "All"

sel = st.session_state.sel

# ── Header + Line selector ────────────────────────────────────────────────────
badges_html = ""

all_class  = "line-btn active-all" if sel == "All" else "line-btn"
all_circle = "background:#fff; color:#495057;" if sel == "All" else "background:#495057; color:#fff;"
all_text   = "#fff" if sel == "All" else "#333"
badges_html += f"""
<a href='?line=All' target='_self' class='{all_class}' style='color:{all_text} !important;'>
    <span class='circle' style='{all_circle}; font-size:0.6rem;'>ALL</span>
    All Lines
</a>"""

for line, cfg in LINE_CONFIG.items():
    is_active    = sel == line
    base_class   = "line-btn " + cfg["active_class"] if is_active else "line-btn"
    circle_style = f"background:#fff; color:{cfg['color']};" if is_active else f"background:{cfg['color']}; color:#fff;"
    text_color   = "#fff" if is_active else "#333"
    badges_html += f"""
    <a href='?line={line}' target='_self' class='{base_class}' style='color:{text_color} !important;'>
        <span class='circle' style='{circle_style}'>{cfg['badge']}</span>
        {cfg['name']}
    </a>"""

st.markdown(f"""
<div class='mbta-header'>
    <div class='mbta-title-row'>
        <div>
            <div class='mbta-header-title'>MBTA Performance Analyzer</div>
            <div class='mbta-header-sub'>Historical subway performance &nbsp;·&nbsp; LAMP data &nbsp;·&nbsp; Last 30 days</div>
        </div>
        <nav class='mbta-nav'>
            <a href='/' target='_self'>Home</a>
        </nav>
    </div>
</div>
<div class='line-selector'>{badges_html}</div>
""", unsafe_allow_html=True)

# ── Derived selection values ──────────────────────────────────────────────────
if sel == "All":
    sel_color = "#495057"
    sel_name  = "All Lines"
    sel_data  = raw
else:
    sel_color = LINE_CONFIG[sel]["color"]
    sel_name  = LINE_CONFIG[sel]["name"]
    sel_data  = raw[raw["line"] == sel]

st.markdown("<div class='content'>", unsafe_allow_html=True)
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
kpis     = kpi_snapshot(raw)
sel_kpis = kpi_snapshot(sel_data)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>System OTP</p>
        <p class='metric-value'>{kpis['otp_pct']}%</p>
        <p class='metric-context'>All lines · last 30 days</p>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>{sel_name} OTP</p>
        <p class='metric-value' style='color:{sel_color};'>{sel_kpis['otp_pct']}%</p>
        <p class='metric-context'>Within ±5 min of schedule</p>
    </div>""", unsafe_allow_html=True)

with c3:
    ett_val = f"{sel_kpis['avg_ett_min']} min" if sel_kpis['avg_ett_min'] is not None else "—"
    rel_val = f"{sel_kpis['pct_reliable']}%" if sel_kpis['pct_reliable'] is not None else "—"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>{sel_name} ETT</p>
        <p class='metric-value' style='color:{sel_color};'>{ett_val}</p>
        <p class='metric-context'>{rel_val} trips reliable (ETT ≤ 5 min)</p>
    </div>""", unsafe_allow_html=True)

with c4:
    hw_val = f"{sel_kpis['pct_adherent']}%" if sel_kpis['pct_adherent'] is not None else "—"
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>{sel_name} Headway</p>
        <p class='metric-value' style='color:{sel_color};'>{hw_val}</p>
        <p class='metric-context'>Trips within ±25% of scheduled gap</p>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class='metric-block'>
        <p class='metric-label'>Records Loaded</p>
        <p class='metric-value'>{kpis['total_records']:,}</p>
        <p class='metric-context'>{kpis['days_covered']} service dates · 4 lines</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── OTP section ───────────────────────────────────────────────────────────────
st.markdown("<p class='section-label'>On-Time Performance</p>", unsafe_allow_html=True)
left, right = st.columns(2)

with left:
    otp_tr = otp_trend(raw)
    if not otp_tr.empty:
        fig = go.Figure()
        for line in SUBWAY_LINES:
            d = otp_tr[otp_tr["line"] == line]
            is_sel = (sel == "All") or (line == sel)
            fig.add_trace(go.Scatter(
                x=d["date"], y=d["otp_pct"],
                mode="lines", name=LINE_CONFIG[line]["name"],
                line=dict(color=LINE_CONFIG[line]["color"], width=2 if is_sel else 1),
                opacity=1.0 if is_sel else 0.2,
            ))
        fig.add_hline(y=80, line_dash="dot", line_color="#ced4da",
                      annotation_text="80% benchmark",
                      annotation_font_size=10, annotation_font_color="#adb5bd")
        fig.update_layout(height=280, **CHART_BASE)
        fig.update_layout(
            yaxis=dict(range=[70, 102], title="OTP (%)",
                       gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    otp_ln = otp_by_line(raw)
    if not otp_ln.empty:
        fig2 = go.Figure(go.Bar(
            x=otp_ln["line"], y=otp_ln["otp_pct"],
            marker_color=bar_colors(otp_ln["line"], sel),
            text=otp_ln["otp_pct"].astype(str) + "%",
            textposition="outside", textfont=dict(size=11),
        ))
        fig2.add_hline(y=80, line_dash="dot", line_color="#ced4da")
        fig2.update_layout(height=280, showlegend=False, **CHART_BASE)
        fig2.update_layout(
            yaxis=dict(range=[0, 107], title="OTP (%)",
                       gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── ETT section ───────────────────────────────────────────────────────────────
st.markdown("<p class='section-label'>Excess Trip Time &nbsp;·&nbsp; 2024 Service Delivery Policy</p>",
            unsafe_allow_html=True)
left2, right2 = st.columns(2)

with left2:
    ett_tr = ett_trend(raw)
    if not ett_tr.empty:
        fig3 = go.Figure()
        for line in SUBWAY_LINES:
            d = ett_tr[ett_tr["line"] == line]
            is_sel = (sel == "All") or (line == sel)
            fig3.add_trace(go.Scatter(
                x=d["date"], y=d["avg_ett_min"],
                mode="lines", name=LINE_CONFIG[line]["name"],
                line=dict(color=LINE_CONFIG[line]["color"], width=2 if is_sel else 1),
                opacity=1.0 if is_sel else 0.2,
            ))
        fig3.add_hline(y=5, line_dash="dot", line_color="#ced4da",
                       annotation_text="5-min threshold",
                       annotation_font_size=10, annotation_font_color="#adb5bd")
        fig3.update_layout(height=280, **CHART_BASE)
        fig3.update_layout(
            yaxis=dict(title="Avg ETT (min)",
                       gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        )
        st.plotly_chart(fig3, use_container_width=True)

with right2:
    ett_ln = ett_by_line(raw)
    if not ett_ln.empty:
        fig4 = go.Figure(go.Bar(
            x=ett_ln["line"], y=ett_ln["avg_ett_min"],
            marker_color=bar_colors(ett_ln["line"], sel),
            text=ett_ln["avg_ett_min"].astype(str) + " min",
            textposition="outside", textfont=dict(size=11),
        ))
        fig4.add_hline(y=5, line_dash="dot", line_color="#DA291C",
                       annotation_text="5-min threshold",
                       annotation_font_size=10, annotation_font_color="#DA291C")
        fig4.update_layout(height=280, showlegend=False, **CHART_BASE)
        fig4.update_layout(
            yaxis=dict(title="Avg ETT (min)",
                       gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
        )
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── Headway section ───────────────────────────────────────────────────────────
st.markdown("<p class='section-label'>Headway Adherence</p>", unsafe_allow_html=True)
left3, right3 = st.columns(2)
hw_ln = headway_by_line(raw)

with left3:
    if not hw_ln.empty:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            name="Scheduled", x=hw_ln["line"], y=hw_ln["avg_scheduled_min"],
            marker_color="#dee2e6",
        ))
        fig5.add_trace(go.Bar(
            name="Actual", x=hw_ln["line"], y=hw_ln["avg_actual_min"],
            marker_color=bar_colors(hw_ln["line"], sel),
        ))
        fig5.update_layout(barmode="group", height=280, **CHART_BASE)
        fig5.update_layout(
            yaxis=dict(title="Minutes", gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        )
        st.plotly_chart(fig5, use_container_width=True)

with right3:
    if not hw_ln.empty:
        fig6 = go.Figure(go.Bar(
            x=hw_ln["line"], y=hw_ln["pct_adherent"],
            marker_color=bar_colors(hw_ln["line"], sel),
            text=hw_ln["pct_adherent"].astype(str) + "%",
            textposition="outside", textfont=dict(size=11),
        ))
        fig6.add_hline(y=75, line_dash="dot", line_color="#ced4da",
                       annotation_text="75% target",
                       annotation_font_size=10, annotation_font_color="#adb5bd")
        fig6.update_layout(height=280, showlegend=False, **CHART_BASE)
        fig6.update_layout(
            yaxis=dict(range=[0, 100], title="% Adherent",
                       gridcolor="#f1f3f5", linecolor="#dee2e6"),
            xaxis=dict(showgrid=False, linecolor="#dee2e6"),
        )
        st.plotly_chart(fig6, use_container_width=True)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── Stop detail section ───────────────────────────────────────────────────────
stop_line = sel if sel != "All" else "Red"
stop_cfg  = LINE_CONFIG[stop_line]
st.markdown(
    f"<p class='section-label'>Stop-Level Performance &nbsp;·&nbsp; "
    f"{'Select a line above to filter' if sel == 'All' else stop_cfg['name']}</p>",
    unsafe_allow_html=True
)

left4, right4 = st.columns(2)

with left4:
    otp_stop = otp_by_stop(raw, stop_line)
    if not otp_stop.empty:
        worst = otp_stop.head(15).copy()
        worst["parent_station"] = worst["parent_station"].apply(clean_stop_name)
        fig7 = go.Figure(go.Bar(
            x=worst["otp_pct"], y=worst["parent_station"],
            orientation="h",
            marker_color=[
                stop_cfg["color"] if v < 98 else "#dee2e6"
                for v in worst["otp_pct"]
            ],
            text=worst["otp_pct"].astype(str) + "%",
            textposition="outside", textfont=dict(size=10),
        ))
        fig7.add_vline(x=97, line_dash="dot", line_color="#ced4da")
        fig7.update_layout(height=max(300, len(worst) * 24), showlegend=False, **CHART_BASE)
        fig7.update_layout(
            xaxis=dict(range=[88, 102], title="OTP (%)",
                       showgrid=False, linecolor="#dee2e6"),
            yaxis=dict(autorange="reversed", linecolor="#dee2e6"),
        )
        st.plotly_chart(fig7, use_container_width=True)

with right4:
    hw_stop = headway_by_stop(raw, stop_line)
    if not hw_stop.empty:
        worst_hw = hw_stop.head(15).copy()
        worst_hw["parent_station"] = worst_hw["parent_station"].apply(clean_stop_name)
        fig8 = go.Figure(go.Bar(
            x=worst_hw["headway_ratio_pct"], y=worst_hw["parent_station"],
            orientation="h",
            marker_color=[
                stop_cfg["color"] if v > 104 else "#dee2e6"
                for v in worst_hw["headway_ratio_pct"]
            ],
            text=worst_hw["headway_ratio_pct"].astype(str) + "%",
            textposition="outside", textfont=dict(size=10),
        ))
        fig8.add_vline(x=100, line_dash="dot", line_color="#ced4da",
                       annotation_text="Scheduled", annotation_font_size=10,
                       annotation_font_color="#adb5bd")
        fig8.update_layout(height=max(300, len(worst_hw) * 24), showlegend=False, **CHART_BASE)
        fig8.update_layout(
            xaxis=dict(title="Actual / Scheduled (%)",
                       showgrid=False, linecolor="#dee2e6"),
            yaxis=dict(autorange="reversed", linecolor="#dee2e6"),
        )
        st.plotly_chart(fig8, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("""
<p style='font-size:0.72rem;color:#adb5bd;text-align:center;padding-bottom:24px;'>
    Built by Tanish Bhilare &nbsp;·&nbsp; MS Data Science, Northeastern University &nbsp;·&nbsp;
    Data: LAMP performancedata.mbta.com &nbsp;·&nbsp;
    <a href='https://github.com/Tashbhilare' style='color:#adb5bd;'>GitHub</a> &nbsp;·&nbsp;
    <a href='https://linkedin.com/in/tanishdhongade' style='color:#adb5bd;'>LinkedIn</a>
</p>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)