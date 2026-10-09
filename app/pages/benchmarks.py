"""Benchmarks page – grouped bars + raw-stats tables, tab per category."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.lib.charts import grouped_bar

# Workload → tab mapping
_TABS = {
    "CPU": ["cpu"],
    "Memory": ["memory"],
    "Disk": ["disk_rand", "disk_seq"],
    "Network": ["network"],
    "Latency": ["redis", "kernel_compile", "vm_lifecycle"],
}


def _stats_table(df: pd.DataFrame, workload: str, metric: str) -> pd.DataFrame:
    """Return a summary stats table for display."""
    sub = df[
        (df["workload"] == workload)
        & (df["metric"] == metric)
        & (df["config"].isin({"direct", "nested"}))
    ]
    if sub.empty:
        return pd.DataFrame()
    stats = (
        sub.groupby("config")["value"]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .round(4)
    )
    return stats


def render(df: pd.DataFrame, is_sample: bool) -> None:
    st.markdown("# 📈 Benchmarks")

    if is_sample:
        st.info("Charts below use **synthetic sample data**.", icon="ℹ️")

    # ── Filters ──────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=False):
        all_workloads = sorted(df["workload"].unique().tolist())
        sel_workloads = st.multiselect(
            "Workloads",
            all_workloads,
            default=all_workloads,
        )
        if "repeat" in df.columns:
            repeats = sorted(df["repeat"].dropna().unique().tolist())
            sel_repeats = st.multiselect("Repeats", repeats, default=repeats)
        else:
            sel_repeats = None

    # Apply filters
    filt = df[df["workload"].isin(sel_workloads)]
    if sel_repeats is not None:
        filt = filt[filt["repeat"].isin(sel_repeats)]

    # ── Tabs ─────────────────────────────────────────────────────────────
    tabs = st.tabs(list(_TABS.keys()))

    for tab, (tab_name, workloads) in zip(tabs, _TABS.items()):
        with tab:
            for wl in workloads:
                if wl not in sel_workloads:
                    continue
                metrics = filt[filt["workload"] == wl]["metric"].unique().tolist()
                if not metrics:
                    st.caption(f"No data for **{wl}**.")
                    continue
                st.markdown(f"#### {wl.replace('_', ' ').title()}")
                cols = st.columns(min(len(metrics), 2))
                for i, metric in enumerate(metrics):
                    with cols[i % len(cols)]:
                        fig = grouped_bar(filt, wl, metric)
                        st.plotly_chart(fig, width='stretch', key=f"bar_{wl}_{metric}")
                        with st.expander(f"📋 Raw stats – {metric}"):
                            tbl = _stats_table(filt, wl, metric)
                            if tbl.empty:
                                st.caption("No data.")
                            else:
                                st.dataframe(tbl, width='stretch')
