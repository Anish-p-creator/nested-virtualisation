"""
Streamlit entry-point for the Nested Virtualization Cost Explorer.

Run:  streamlit run app/main.py
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.lib.data_loader import load_data, validate_dataframe

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nested Virtualization Cost Explorer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* KPI card styling */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(74,144,217,0.08), rgba(232,136,60,0.08));
        border: 1px solid rgba(128,128,128,0.15);
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="stMetric"] label {
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        opacity: 0.7;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* Sample-data banner */
    .sample-banner {
        background: linear-gradient(90deg, #D97706, #EA580C);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        letter-spacing: 0.04em;
        margin-bottom: 16px;
        animation: pulse 2.5s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.85; }
    }

    /* Recommendation badges */
    .badge-keep   { background:#16A34A; color:white; padding:6px 16px; border-radius:20px; font-weight:600; display:inline-block; }
    .badge-upsize { background:#D97706; color:white; padding:6px 16px; border-radius:20px; font-weight:600; display:inline-block; }
    .badge-dedi   { background:#DC2626; color:white; padding:6px 16px; border-radius:20px; font-weight:600; display:inline-block; }

    /* Sidebar polish */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,0.15);
    }

    /* Tab styling */
    button[data-baseweb="tab"] {
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Sidebar: navigation + upload ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 Cost Explorer")
    page = st.radio(
        "Navigate",
        ["Overview", "Benchmarks", "Concurrency", "Cost Calculator", "Methodology"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("#### 📂 Data Source")
    uploaded = st.file_uploader(
        "Upload benchmark CSV",
        type=["csv"],
        help="Must match the expected schema (see Methodology page).",
    )
    st.divider()
    st.caption("Built with Streamlit · Plotly · Pandas")


# ── Load data ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading benchmark data…")
def _load(upload_bytes):
    return load_data(upload_bytes)


upload_arg = uploaded if uploaded is not None else None
df, is_sample = _load(upload_arg)

# Validate
errors = validate_dataframe(df)
if errors:
    for e in errors:
        st.warning(e)

# Sample banner
if is_sample:
    st.markdown(
        '<div class="sample-banner">⚠️ SAMPLE DATA – NOT REAL MEASUREMENTS</div>',
        unsafe_allow_html=True,
    )

# Store in session for pages
st.session_state["df"] = df
st.session_state["is_sample"] = is_sample


# ── Route to page ────────────────────────────────────────────────────────
if page == "Overview":
    from app.pages.overview import render
elif page == "Benchmarks":
    from app.pages.benchmarks import render
elif page == "Concurrency":
    from app.pages.concurrency import render
elif page == "Cost Calculator":
    from app.pages.cost_calculator import render
else:
    from app.pages.methodology import render

render(df, is_sample)
