"""Overview page – KPI cards + plain-English summary."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.lib.cost_model import (
    cpu_overhead_pct,
    p99_latency_change_pct,
    e_capacity_from_df,
    cost_per_1000_jobs,
)


def render(df: pd.DataFrame, is_sample: bool) -> None:
    st.markdown("# 📊 Overview")

    if is_sample:
        st.info("The numbers below are from **synthetic sample data** and do not represent real measurements.", icon="ℹ️")

    # ── Compute KPIs ─────────────────────────────────────────────────────
    cpu_oh = cpu_overhead_pct(df)
    p99_change = p99_latency_change_pct(df)
    e_cap = e_capacity_from_df(df)

    # Cost per 1k jobs (use default rates for the overview)
    HOURLY_RATE = 0.50  # $/hr placeholder
    MONTHLY_HOURS = 720.0

    direct_cpu_sec = df[
        (df["config"] == "direct") & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")
    ]["value"]
    nested_cpu_sec = df[
        (df["config"].isin({"nested", "nested-1"})) & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")
    ]["value"]

    direct_c1k = cost_per_1000_jobs(HOURLY_RATE, direct_cpu_sec.median(), MONTHLY_HOURS) if not direct_cpu_sec.empty else None
    nested_c1k = cost_per_1000_jobs(HOURLY_RATE, nested_cpu_sec.median(), MONTHLY_HOURS) if not nested_cpu_sec.empty else None

    # ── KPI cards ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "CPU Overhead",
            f"{cpu_oh:.1f} %" if cpu_oh is not None else "N/A",
            help="Throughput drop (events/s) for nested vs direct.",
        )
    with c2:
        st.metric(
            "P99 Latency Change",
            f"+{p99_change:.1f} %" if p99_change is not None else "N/A",
            help="Average p99 latency increase across all workloads.",
        )
    with c3:
        st.metric(
            "Capacity Premium (E)",
            f"{e_cap:.1%}" if e_cap is not None else "N/A",
            help="Extra CPU-seconds needed per job when nested.",
        )
    with c4:
        col_left, col_right = st.columns(2)
        with col_left:
            st.metric(
                "Direct $/1 k jobs",
                f"${direct_c1k:.2f}" if direct_c1k is not None else "N/A",
            )
        with col_right:
            st.metric(
                "Nested $/1 k jobs",
                f"${nested_c1k:.2f}" if nested_c1k is not None else "N/A",
            )

    # ── Summary ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 💡 Summary")

    if cpu_oh is not None and e_cap is not None:
        summary_parts = []
        summary_parts.append(
            f"Running workloads in a **nested (L2) VM** introduces approximately "
            f"**{cpu_oh:.1f} %** CPU throughput overhead compared to a direct VM."
        )
        if p99_change is not None:
            summary_parts.append(
                f"Tail latency (p99) increases by an average of **{p99_change:.1f} %** across measured workloads."
            )
        summary_parts.append(
            f"The capacity premium **E = {e_cap:.1%}** means each nested job "
            f"consumes roughly **{e_cap:.0%} more CPU-seconds** than the same job on bare metal."
        )
        if direct_c1k is not None and nested_c1k is not None:
            diff = nested_c1k - direct_c1k
            summary_parts.append(
                f"At a base rate of **${HOURLY_RATE}/hr**, nesting costs "
                f"**${diff:+.2f}** more per 1,000 jobs "
                f"(${nested_c1k:.2f} vs ${direct_c1k:.2f})."
            )
        if e_cap < 0.20:
            summary_parts.append(
                "This overhead is **moderate** and likely acceptable for most workloads. "
                "Head to the **Cost Calculator** to model your specific scenario."
            )
        else:
            summary_parts.append(
                "This overhead is **significant**. Consider checking the **Cost Calculator** "
                "to see if upsizing the VM would be more economical."
            )
        st.markdown("\n\n".join(summary_parts))
    else:
        st.warning("Insufficient data to generate a summary. Make sure your CSV contains `cpu` workload rows with `events_per_sec` and `cpu_seconds_per_job` metrics.")
