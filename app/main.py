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

    /* Main App Background (Optional dark mode enforcement) */
    .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #151923 100%);
    }

    /* KPI card styling with Glassmorphism & Hover */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), border 0.3s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(74, 144, 217, 0.4);
    }
    div[data-testid="stMetric"] label {
        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #94A3B8;
        opacity: 1;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-weight: 800;
        font-size: 2.2rem;
        background: linear-gradient(90deg, #4A90D9, #E8883C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-top: 5px;
    }

    /* Sample-data banner */
    .sample-banner {
        background: linear-gradient(90deg, #F59E0B, #EF4444);
        color: white;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.05em;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        animation: pulse 3s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.9; transform: scale(0.995); }
    }

    /* Recommendation badges with Neon Glow */
    .badge-keep   { background: linear-gradient(135deg, #10B981, #059669); color:white; padding:8px 24px; border-radius:30px; font-weight:800; display:inline-block; box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); text-transform: uppercase; letter-spacing: 1px;}
    .badge-upsize { background: linear-gradient(135deg, #F59E0B, #D97706); color:white; padding:8px 24px; border-radius:30px; font-weight:800; display:inline-block; box-shadow: 0 0 20px rgba(245, 158, 11, 0.4); text-transform: uppercase; letter-spacing: 1px;}
    .badge-dedi   { background: linear-gradient(135deg, #EF4444, #DC2626); color:white; padding:8px 24px; border-radius:30px; font-weight:800; display:inline-block; box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); text-transform: uppercase; letter-spacing: 1px;}

    /* Sidebar polish */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    section[data-testid="stSidebar"] .stRadio label {
        font-weight: 500;
        transition: color 0.2s;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        color: #4A90D9;
    }

    /* Headers and Titles */
    h1, h2, h3 {
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }
    h1 {
        background: linear-gradient(120deg, #FFFFFF, #94A3B8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px !important;
    }

    /* Tab styling */
    button[data-baseweb="tab"] {
        font-weight: 600;
        transition: all 0.2s ease;
    }
    button[data-baseweb="tab"]:hover {
        color: #E8883C !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        border-radius: 8px;
        transition: background-color 0.2s;
    }
    .streamlit-expanderHeader:hover {
        background-color: rgba(255,255,255,0.05);
    }
    
    /* Input widgets focus states */
    .stTextInput input, .stNumberInput input {
        border-radius: 8px;
        transition: border-color 0.3s, box-shadow 0.3s;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        box-shadow: 0 0 0 2px rgba(74, 144, 217, 0.3);
        border-color: #4A90D9;
    }
    
    /* Make tables look better */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
