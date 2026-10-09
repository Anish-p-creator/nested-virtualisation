"""Cost Calculator page – interactive what-if analysis."""
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.lib.cost_model import (
    e_capacity_from_df,
    cost_nested,
    cost_per_1000_jobs,
    recommend,
    sensitivity_table,
)
from app.lib.charts import sensitivity_chart


def render(df: pd.DataFrame, is_sample: bool) -> None:
    st.markdown("# 🧮 Cost Calculator")

    if is_sample:
        st.info("Default overhead values come from **synthetic sample data**.", icon="ℹ️")

    # ── Measured E_capacity (default) ────────────────────────────────────
    measured_e = e_capacity_from_df(df)
    default_e = round(measured_e * 100, 1) if measured_e is not None else 13.0

    # ── Inputs ───────────────────────────────────────────────────────────
    st.markdown("### Instance Pricing")
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        base_price = st.number_input(
            "Base instance $/hr",
            min_value=0.01,
            value=0.50,
            step=0.05,
            format="%.2f",
            key="calc_base",
        )
    with ic2:
        larger_price = st.number_input(
            "Larger instance $/hr",
            min_value=0.01,
            value=0.85,
            step=0.05,
            format="%.2f",
            key="calc_larger",
        )
    with ic3:
        capacity_mult = st.number_input(
            "Capacity multiplier (larger)",
            min_value=1.0,
            value=2.0,
            step=0.1,
            format="%.1f",
            key="calc_cap_mult",
            help="How many times more throughput the larger instance provides.",
        )

    st.markdown("### Workload Parameters")
    wc1, wc2 = st.columns(2)
    with wc1:
        monthly_cpu_hours = st.number_input(
            "Monthly useful CPU-hours",
            min_value=1.0,
            value=720.0,
            step=10.0,
            key="calc_hours",
        )
    with wc2:
        operational_cost = st.number_input(
            "Monthly operational cost ($)",
            min_value=0.0,
            value=0.0,
            step=5.0,
            format="%.2f",
            key="calc_ops",
            help="Extra cost for managing the nested setup (tooling, monitoring, etc.).",
        )

    st.markdown("### Overhead Tolerance")
    p_max = st.slider(
        "Maximum acceptable overhead (P_max)",
        min_value=0,
        max_value=60,
        value=25,
        step=1,
        format="%d %%",
        key="calc_pmax",
    )
    p_max_frac = p_max / 100.0

    # ── Compute ──────────────────────────────────────────────────────────
    # CPU seconds per job from data
    direct_cpu_sec = df[
        (df["config"] == "direct") & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")
    ]["value"]
    nested_cpu_sec = df[
        (df["config"].isin({"nested", "nested-1"})) & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")
    ]["value"]

    if direct_cpu_sec.empty or nested_cpu_sec.empty:
        st.warning("Missing `cpu_seconds_per_job` data. Cannot compute costs.")
        return

    d_sec = direct_cpu_sec.median()
    n_sec = nested_cpu_sec.median()
    e_cap = (n_sec / d_sec) - 1

    # Monthly costs
    base_monthly = base_price * monthly_cpu_hours
    c_nested_monthly = cost_nested(base_monthly, e_cap, operational_cost)
    larger_monthly = larger_price * monthly_cpu_hours

    # Per-1k-jobs costs
    direct_c1k = cost_per_1000_jobs(base_price, d_sec, monthly_cpu_hours)
    nested_c1k = cost_per_1000_jobs(base_price, n_sec, monthly_cpu_hours)
    # Larger instance: assume direct perf, higher price
    larger_c1k = cost_per_1000_jobs(larger_price, d_sec / capacity_mult, monthly_cpu_hours)

    # Decision
    decision, reason = recommend(e_cap, p_max_frac, nested_c1k, direct_c1k, larger_c1k)

    # ── Output ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Results")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("E_capacity", f"{e_cap:.1%}")
    with rc2:
        st.metric("C_nested (monthly)", f"${c_nested_monthly:,.2f}")
    with rc3:
        st.metric("Larger instance (monthly)", f"${larger_monthly:,.2f}")

    st.markdown("#### Cost per 1,000 Jobs")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.metric("Direct", f"${direct_c1k:.4f}")
    with cc2:
        st.metric("Nested", f"${nested_c1k:.4f}")
    with cc3:
        st.metric("Larger Instance", f"${larger_c1k:.4f}")

    # ── Recommendation badge ─────────────────────────────────────────────
    st.divider()
    badge_class = {
        "Keep nesting": "badge-keep",
        "Upsize VM": "badge-upsize",
        "Go dedicated": "badge-dedi",
    }
    st.markdown(
        f'<div style="text-align: center; margin: 20px 0;"><span class="{badge_class[decision]}">{decision}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"> **{reason}**")
    
    # Dynamic interactions based on decision
    if st.session_state.get('last_decision') != decision:
        st.session_state['last_decision'] = decision
        if decision == "Keep nesting":
            st.balloons()
        elif decision == "Go dedicated":
            st.snow()

    # ── Sensitivity chart ────────────────────────────────────────────────
    st.divider()
    st.markdown("### Sensitivity Analysis")
    sens = sensitivity_table(base_monthly, operational_cost, 0.0, 0.60)
    fig = sensitivity_chart(sens, base_cost=base_monthly)
    st.plotly_chart(fig, width='stretch')

    # ── Downloadable CSV ─────────────────────────────────────────────────
    results_df = pd.DataFrame(
        {
            "Metric": [
                "E_capacity",
                "Direct $/1k jobs",
                "Nested $/1k jobs",
                "Larger $/1k jobs",
                "C_nested monthly",
                "Larger monthly",
                "Recommendation",
            ],
            "Value": [
                f"{e_cap:.4f}",
                f"{direct_c1k:.4f}",
                f"{nested_c1k:.4f}",
                f"{larger_c1k:.4f}",
                f"{c_nested_monthly:.2f}",
                f"{larger_monthly:.2f}",
                decision,
            ],
        }
    )
    st.download_button(
        "⬇️  Download results CSV",
        data=results_df.to_csv(index=False),
        file_name="cost_calculator_results.csv",
        mime="text/csv",
    )
