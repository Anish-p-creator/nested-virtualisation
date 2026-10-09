"""Concurrency page – cost & latency vs number of concurrent L2 VMs."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.lib.cost_model import (
    concurrency_table,
    latency_concurrency_table,
    break_even_concurrency,
)
from app.lib.charts import concurrency_cost_chart, concurrency_latency_chart


def render(df: pd.DataFrame, is_sample: bool) -> None:
    st.markdown("# 🔄 Concurrency Scaling")

    if is_sample:
        st.info("Charts below use **synthetic sample data**.", icon="ℹ️")

    # ── Sidebar-like controls ────────────────────────────────────────────
    with st.expander("⚙️ Parameters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            workload = st.selectbox(
                "Workload",
                sorted(df["workload"].unique().tolist()),
                index=0,
                key="conc_wl",
            )
        with c2:
            available_metrics = sorted(
                df[df["workload"] == workload]["metric"].unique().tolist()
            )
            # prefer cpu_seconds_per_job if present
            default_idx = 0
            if "cpu_seconds_per_job" in available_metrics:
                default_idx = available_metrics.index("cpu_seconds_per_job")
            metric = st.selectbox(
                "Metric (for cost curve)",
                available_metrics,
                index=default_idx,
                key="conc_metric",
            )
        with c3:
            hourly_rate = st.number_input(
                "Instance $/hr",
                min_value=0.01,
                value=0.50,
                step=0.05,
                format="%.2f",
                key="conc_rate",
            )

    c4, c5 = st.columns(2)
    with c4:
        larger_rate = st.number_input(
            "Larger instance $/hr",
            min_value=0.01,
            value=0.85,
            step=0.05,
            format="%.2f",
            key="conc_larger",
        )
    with c5:
        monthly_hours = st.number_input(
            "Monthly CPU-hours",
            min_value=1.0,
            value=720.0,
            step=10.0,
            key="conc_hours",
        )

    # ── Compute ──────────────────────────────────────────────────────────
    ct = concurrency_table(df, workload, metric, hourly_rate, monthly_hours)
    lt = latency_concurrency_table(df, workload)
    be = break_even_concurrency(
        df, hourly_rate, larger_rate, monthly_hours, workload, metric
    )

    if ct.empty:
        st.warning(
            f"No concurrency data found for **{workload} / {metric}**. "
            "Make sure your CSV includes `nested-1`, `nested-2`, `nested-4`, `nested-8` configs."
        )
        return

    # ── Charts ───────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            concurrency_cost_chart(ct, break_even=be),
            width='stretch',
        )
    with col_b:
        st.plotly_chart(
            concurrency_latency_chart(lt),
            width='stretch',
        )

    # ── Break-even annotation ────────────────────────────────────────────
    if be is not None:
        st.success(
            f"**Break-even point: {be} concurrent L2 VMs.** "
            f"Beyond this, upsizing to a ${larger_rate:.2f}/hr instance is cheaper per job.",
            icon="📍",
        )
    else:
        st.info(
            "Nesting remains cheaper across all measured concurrency levels "
            f"(up to 8 VMs at ${hourly_rate:.2f}/hr vs a ${larger_rate:.2f}/hr instance).",
            icon="✅",
        )

    # ── Data table ───────────────────────────────────────────────────────
    with st.expander("📋 Concurrency data table"):
        st.dataframe(ct, width='stretch')
