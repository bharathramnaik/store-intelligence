from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Apex Retail Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern glassmorphism dashboard
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        transition: transform 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
    }

    .metric-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        line-height: 1;
    }

    .metric-delta-positive {
        color: #10b981;
        font-size: 0.9rem;
        font-weight: 600;
    }

    .metric-delta-negative {
        color: #ef4444;
        font-size: 0.9rem;
        font-weight: 600;
    }

    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .pulse {
        width: 8px;
        height: 8px;
        background: #10b981;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .anomaly-card-critical {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left: 4px solid #dc2626;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .anomaly-card-warn {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #d97706;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .anomaly-card-info {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-left: 4px solid #2563eb;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .stale-badge {
        background: #fee2e2;
        color: #dc2626;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .active-badge {
        background: #d1fae5;
        color: #059669;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def fetch(endpoint: str, timeout: float = 10.0):
    try:
        r = httpx.get(f"{API_BASE}{endpoint}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"🔌 API Error: {exc}")
        return None


# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shop.png", width=60)
    st.title("Apex Retail")
    st.caption("Store Intelligence Platform")
    st.divider()

    store_id = st.selectbox(
        "🏪 Select Store",
        ["STORE_BLR_002", "STORE_BLR_003", "STORE_MUM_001", "STORE_DEL_001", "STORE_HYD_001"],
        index=0,
    )

    refresh = st.slider("🔄 Refresh Interval (sec)", 5, 60, 10)

    st.divider()
    st.subheader("📊 Quick Links")
    st.page_link("http://localhost:8000/docs", label="API Docs", icon="📡")
    st.page_link("http://localhost:8000/health", label="Health Check", icon="🏥")

    st.divider()
    st.caption("v0.1.0 • Built with FastAPI + Streamlit")

# Header
header_col1, header_col2, header_col3 = st.columns([3, 2, 1])
with header_col1:
    st.markdown("<h1 style='color: white; margin: 0;'>🛍️ Store Intelligence</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: rgba(255,255,255,0.8); margin-top: 4px;'>Real-time analytics from CCTV footage</p>", unsafe_allow_html=True)

with header_col3:
    st.markdown(
        f"""
        <div class="live-indicator">
            <div class="pulse"></div>
            LIVE • {datetime.now(timezone.utc).strftime("%H:%M:%S UTC")}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Auto-refresh
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > refresh:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Fetch all data
metrics = fetch(f"/stores/{store_id}/metrics")
funnel = fetch(f"/stores/{store_id}/funnel")
heatmap = fetch(f"/stores/{store_id}/heatmap")
anomalies = fetch(f"/stores/{store_id}/anomalies")
health = fetch("/health")

# Metrics Row
if metrics:
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">👥 Unique Visitors</div>
                <div class="metric-value">{metrics.get("unique_visitors", 0):,}</div>
            </div>
        """, unsafe_allow_html=True)

    with m2:
        conv = metrics.get("conversion_rate", 0) * 100
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💰 Conversion Rate</div>
                <div class="metric-value">{conv:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⏱️ Avg Dwell</div>
                <div class="metric-value">{sum(metrics.get("avg_dwell_per_zone", {}).values()) / max(len(metrics.get("avg_dwell_per_zone", {})), 1) / 1000:.1f}s</div>
            </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🛒 Queue Depth</div>
                <div class="metric-value">{metrics.get("queue_depth", 0)}</div>
            </div>
        """, unsafe_allow_html=True)

    with m5:
        abandon = metrics.get("abandonment_rate", 0) * 100
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🏃 Abandonment</div>
                <div class="metric-value">{abandon:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Content: Two columns
left_col, right_col = st.columns([2, 1])

with left_col:
    # Funnel Chart
    st.markdown("<div class='section-header'>🎯 Conversion Funnel</div>", unsafe_allow_html=True)
    if funnel and funnel.get("stages"):
        stages = funnel["stages"]
        df_funnel = pd.DataFrame(stages)

        fig = go.Figure(go.Funnel(
            y = df_funnel["stage"],
            x = df_funnel["count"],
            textposition = "inside",
            textinfo = "value+percent initial",
            opacity = 0.85,
            marker = {
                "color": ["#6366f1", "#8b5cf6", "#ec4899", "#10b981"],
                "line": {"color": "white", "width": 2}
            },
            connector = {"line": {"color": "rgba(255,255,255,0.5)", "dash": "dot"}}
        ))
        fig.update_layout(
            funnelmode="stack",
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=14, color="white"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No funnel data available")

    # Heatmap
    st.markdown("<div class='section-header'>🔥 Zone Heatmap</div>", unsafe_allow_html=True)
    if heatmap and heatmap.get("zones"):
        df_heat = pd.DataFrame(heatmap["zones"])

        fig2 = make_subplots(rows=1, cols=2, subplot_titles=("Visit Frequency", "Avg Dwell (ms)"), specs=[[{"type": "bar"}, {"type": "bar"}]])

        fig2.add_trace(
            go.Bar(
                x=df_heat["zone_id"], 
                y=df_heat["visit_frequency"], 
                marker_color="#6366f1",
                name="Visits"
            ), 
            row=1, col=1
        )
        fig2.add_trace(
            go.Bar(
                x=df_heat["zone_id"], 
                y=df_heat["avg_dwell_ms"], 
                marker_color="#ec4899",
                name="Dwell"
            ), 
            row=1, col=2
        )

        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=12, color="white"),
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

        confidence = heatmap.get("data_confidence", "UNKNOWN")
        badge_color = "#10b981" if confidence == "HIGH" else "#f59e0b"
        st.markdown(f"""
            <div style="text-align: right;">
                <span style="background: {badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                    Data Confidence: {confidence}
                </span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No heatmap data available")

with right_col:
    # Anomalies Panel
    st.markdown("<div class='section-header'>⚠️ Active Anomalies</div>", unsafe_allow_html=True)
    if anomalies:
        for anom in anomalies:
            severity = anom.get("severity", "INFO")
            card_class = f"anomaly-card-{severity.lower()}"
            icon = "🔴" if severity == "CRITICAL" else "🟠" if severity == "WARN" else "🔵"

            st.markdown(f"""
                <div class="{card_class}">
                    <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 6px;">
                        {icon} {anom['anomaly_type']}
                    </div>
                    <div style="font-size: 0.85rem; color: #4b5563; margin-bottom: 8px;">
                        {anom['message']}
                    </div>
                    <div style="font-size: 0.8rem; color: #6b7280; font-style: italic;">
                        💡 {anom['suggested_action']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 20px; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 8px;">✅</div>
                <div style="font-weight: 600; color: #059669;">All Systems Normal</div>
                <div style="font-size: 0.85rem; color: #6b7280;">No active anomalies detected</div>
            </div>
        """, unsafe_allow_html=True)

    # Health Status
    st.markdown("<div class='section-header'>🏥 System Health</div>", unsafe_allow_html=True)
    if health:
        service_status = health.get("service", "unknown")
        st.markdown(f"""
            <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-weight: 600; color: #374151;">API Service</span>
                    <span class="{'active-badge' if service_status == 'healthy' else 'stale-badge'}">
                        {service_status.upper()}
                    </span>
                </div>
        """, unsafe_allow_html=True)

        for store in health.get("stores", []):
            status = store.get("status", "UNKNOWN")
            last_ts = store.get("last_event_timestamp")
            last_str = datetime.fromisoformat(last_ts.replace("Z", "+00:00")).strftime("%H:%M") if last_ts else "Never"
            badge = "active-badge" if status == "ACTIVE" else "stale-badge"

            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <div>
                        <div style="font-weight: 500; color: #1f2937; font-size: 0.9rem;">{store['store_id']}</div>
                        <div style="font-size: 0.75rem; color: #6b7280;">Last event: {last_str}</div>
                    </div>
                    <span class="{badge}">{status}</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Health data unavailable")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; color: rgba(255,255,255,0.6); font-size: 0.8rem; padding: 20px;">
        Apex Retail Intelligence • Real-time Store Analytics • Built for Purplle Tech Challenge 2026
    </div>
""", unsafe_allow_html=True)
