"""
Plotly chart builders.

Every function returns a plotly Figure – the Streamlit layer just calls
st.plotly_chart(fig).
"""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ── Color palette ────────────────────────────────────────────────────────
COLORS = {
    "direct": "#4A90D9",       # blue
    "nested": "#E8883C",       # orange
    "nested-1": "#E8883C",
    "nested-2": "#D4644E",
    "nested-4": "#C04060",
    "nested-8": "#A01C72",
}

_LAYOUT_COMMON = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", size=13),
    margin=dict(l=60, r=30, t=50, b=50),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _apply_layout(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(**_LAYOUT_COMMON, **kwargs)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    return fig


# ── Grouped bar chart (Benchmarks page) ─────────────────────────────────

def grouped_bar(
    df: pd.DataFrame,
    workload: str,
    metric: str,
    title: str | None = None,
) -> go.Figure:
    """
    Grouped bar: direct vs nested for the given workload + metric.
    Shows median with error bars (p5 → p95).
    """
    configs_order = ["direct", "nested"]
    sub = df[
        (df["workload"] == workload)
        & (df["metric"] == metric)
        & (df["config"].isin(configs_order))
    ]
    if sub.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False, font=dict(size=18))
        return _apply_layout(fig, title=title or f"{workload} – {metric}")

    stats = (
        sub.groupby("config")["value"]
        .agg(["median", lambda x: x.quantile(0.05), lambda x: x.quantile(0.95)])
        .rename(columns={"median": "med", "<lambda_0>": "p5", "<lambda_1>": "p95"})
        .reindex(configs_order)
    )

    unit = sub["unit"].iloc[0] if "unit" in sub.columns else ""

    fig = go.Figure()
    for cfg in configs_order:
        if cfg not in stats.index or pd.isna(stats.loc[cfg, "med"]):
            continue
        med = stats.loc[cfg, "med"]
        err_minus = max(med - stats.loc[cfg, "p5"], 0)
        err_plus = max(stats.loc[cfg, "p95"] - med, 0)
        fig.add_trace(
            go.Bar(
                x=[cfg],
                y=[med],
                name=cfg.capitalize(),
                marker_color=COLORS.get(cfg, "#888"),
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[err_plus],
                    arrayminus=[err_minus],
                    color="rgba(255,255,255,0.5)",
                    thickness=1.5,
                ),
                hovertemplate=f"%{{x}}<br>Median: %{{y:.4g}} {unit}<extra></extra>",
            )
        )

    return _apply_layout(
        fig,
        title=title or f"{workload} – {metric}",
        yaxis_title=unit,
        barmode="group",
        showlegend=True,
    )


# ── Concurrency line chart ───────────────────────────────────────────────

def concurrency_cost_chart(ct: pd.DataFrame, break_even: int | None = None) -> go.Figure:
    """Line chart of cost per 1 k jobs vs concurrency."""
    if ct.empty:
        fig = go.Figure()
        fig.add_annotation(text="No concurrency data", showarrow=False, font=dict(size=18))
        return _apply_layout(fig)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ct["concurrency"],
            y=ct["cost_per_1000_jobs"],
            mode="lines+markers",
            name="Cost / 1 k jobs",
            line=dict(color=COLORS["nested"], width=2.5),
            marker=dict(size=9),
            hovertemplate="VMs: %{x}<br>$%{y:.2f} / 1k jobs<extra></extra>",
        )
    )
    if break_even is not None:
        fig.add_vline(
            x=break_even,
            line_dash="dash",
            line_color="#EF4444",
            annotation_text=f"Break-even ({break_even} VMs)",
            annotation_position="top right",
            annotation_font_color="#EF4444",
        )
    return _apply_layout(fig, title="Cost per 1,000 Jobs vs Concurrency", xaxis_title="Concurrent L2 VMs", yaxis_title="$ / 1,000 jobs")


def concurrency_latency_chart(lt: pd.DataFrame) -> go.Figure:
    """Line chart of p95 / p99 latency vs concurrency."""
    if lt.empty:
        fig = go.Figure()
        fig.add_annotation(text="No latency data", showarrow=False, font=dict(size=18))
        return _apply_layout(fig)

    fig = go.Figure()
    for col, color, dash in [
        ("p95_latency", "#FBBF24", "solid"),
        ("p99_latency", "#EF4444", "dot"),
    ]:
        if col in lt.columns:
            fig.add_trace(
                go.Scatter(
                    x=lt["concurrency"],
                    y=lt[col],
                    mode="lines+markers",
                    name=col.replace("_", " ").upper(),
                    line=dict(color=color, width=2.5, dash=dash),
                    marker=dict(size=9),
                    hovertemplate="VMs: %{x}<br>%{y:.3f} ms<extra></extra>",
                )
            )
    return _apply_layout(fig, title="Tail Latency vs Concurrency", xaxis_title="Concurrent L2 VMs", yaxis_title="Latency (ms)")


# ── Sensitivity chart ────────────────────────────────────────────────────

def sensitivity_chart(sens: pd.DataFrame, base_cost: float | None = None) -> go.Figure:
    """Cost vs E_capacity (%) line chart."""
    if sens.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", showarrow=False, font=dict(size=18))
        return _apply_layout(fig)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sens["E_capacity_pct"],
            y=sens["C_nested"],
            mode="lines",
            name="C_nested",
            line=dict(color=COLORS["nested"], width=3),
            fill="tozeroy",
            fillcolor="rgba(232,136,60,0.12)",
            hovertemplate="E_cap: %{x:.1f}%<br>$%{y:.2f}<extra></extra>",
        )
    )
    if base_cost is not None:
        fig.add_hline(
            y=base_cost,
            line_dash="dash",
            line_color=COLORS["direct"],
            annotation_text=f"Direct cost: ${base_cost:.2f}",
            annotation_position="bottom right",
            annotation_font_color=COLORS["direct"],
        )
    return _apply_layout(
        fig,
        title="Sensitivity: Nested Cost vs Capacity Premium",
        xaxis_title="E_capacity (%)",
        yaxis_title="Monthly Cost ($)",
    )
