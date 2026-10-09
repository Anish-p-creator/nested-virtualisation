"""
Pure cost-model functions.

No Streamlit imports – every function is deterministic and unit-testable.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


# ── Core metrics ─────────────────────────────────────────────────────────

def capacity_premium(
    nested_cpu_seconds: float,
    direct_cpu_seconds: float,
) -> float:
    """
    E_capacity = (nested CPU-seconds per job / direct CPU-seconds per job) - 1

    Returns a fraction (e.g. 0.13 means 13 % overhead).
    Raises ValueError when direct_cpu_seconds <= 0.
    """
    if direct_cpu_seconds <= 0:
        raise ValueError("direct_cpu_seconds must be > 0")
    return (nested_cpu_seconds / direct_cpu_seconds) - 1


def cost_nested(
    base_cost: float,
    e_capacity: float,
    operational_cost: float = 0.0,
) -> float:
    """C_nested = C_base × (1 + E_capacity) + C_operational"""
    return base_cost * (1 + e_capacity) + operational_cost


def cost_per_1000_jobs(
    hourly_rate: float,
    cpu_seconds_per_job: float,
    monthly_cpu_hours: float,
) -> float:
    """
    Monthly cost for running 1,000 jobs given an hourly VM rate.
    jobs_per_month = monthly_cpu_hours * 3600 / cpu_seconds_per_job
    cost_per_job   = hourly_rate * monthly_cpu_hours / jobs_per_month
    cost_per_1000  = cost_per_job * 1000
    """
    if cpu_seconds_per_job <= 0 or monthly_cpu_hours <= 0:
        return float("nan")
    jobs_per_month = monthly_cpu_hours * 3600 / cpu_seconds_per_job
    if jobs_per_month <= 0:
        return float("nan")
    monthly_cost = hourly_rate * monthly_cpu_hours
    return (monthly_cost / jobs_per_month) * 1000


# ── Overhead helpers ─────────────────────────────────────────────────────

def compute_overhead_pct(
    df: pd.DataFrame,
    workload: str,
    metric: str,
) -> float | None:
    """
    Compute percentage overhead of nested vs direct for a given
    workload + metric.  Returns None if insufficient data.

    For throughput-like metrics (higher is better) overhead =
        (direct - nested) / direct × 100
    For latency-like metrics (lower is better) overhead =
        (nested - direct) / direct × 100
    """
    is_lower_better = any(
        kw in metric for kw in ("latency", "time", "seconds")
    )
    direct = df[(df["config"] == "direct") & (df["workload"] == workload) & (df["metric"] == metric)]["value"]
    nested = df[(df["config"].isin({"nested", "nested-1"})) & (df["workload"] == workload) & (df["metric"] == metric)]["value"]
    if direct.empty or nested.empty:
        return None
    d_med = direct.median()
    n_med = nested.median()
    if d_med == 0:
        return None
    if is_lower_better:
        return ((n_med - d_med) / d_med) * 100
    else:
        return ((d_med - n_med) / d_med) * 100


def cpu_overhead_pct(df: pd.DataFrame) -> float | None:
    """CPU overhead (%) based on cpu / events_per_sec."""
    return compute_overhead_pct(df, "cpu", "events_per_sec")


def p99_latency_change_pct(df: pd.DataFrame) -> float | None:
    """Average p99 latency change (%) across all workloads that have it."""
    vals = []
    for wl in df["workload"].unique():
        v = compute_overhead_pct(df, wl, "p99_latency")
        if v is not None:
            vals.append(v)
    return float(np.mean(vals)) if vals else None


def e_capacity_from_df(df: pd.DataFrame) -> float | None:
    """Derive E_capacity from cpu / cpu_seconds_per_job rows."""
    direct = df[(df["config"] == "direct") & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")]["value"]
    nested = df[(df["config"].isin({"nested", "nested-1"})) & (df["workload"] == "cpu") & (df["metric"] == "cpu_seconds_per_job")]["value"]
    if direct.empty or nested.empty:
        return None
    try:
        return capacity_premium(nested.median(), direct.median())
    except ValueError:
        return None


# ── Concurrency analysis ─────────────────────────────────────────────────

_CONCURRENCY_MAP = {
    "nested-1": 1,
    "nested-2": 2,
    "nested-4": 4,
    "nested-8": 8,
}


def concurrency_table(
    df: pd.DataFrame,
    workload: str = "cpu",
    metric: str = "cpu_seconds_per_job",
    hourly_rate: float = 1.0,
    monthly_cpu_hours: float = 720.0,
) -> pd.DataFrame:
    """
    Build a table with columns [concurrency, median_value, p95, p99,
    cost_per_1000_jobs] for the given workload + metric across
    nested-1 … nested-8 configs.
    """
    rows = []
    for cfg, n_vms in _CONCURRENCY_MAP.items():
        subset = df[(df["config"] == cfg) & (df["workload"] == workload) & (df["metric"] == metric)]["value"]
        if subset.empty:
            continue
        med = subset.median()
        rows.append(
            {
                "concurrency": n_vms,
                "config": cfg,
                "median_value": med,
                "p95": subset.quantile(0.95) if len(subset) >= 2 else med,
                "p99": subset.quantile(0.99) if len(subset) >= 2 else med,
                "cost_per_1000_jobs": cost_per_1000_jobs(hourly_rate, med, monthly_cpu_hours),
            }
        )
    return pd.DataFrame(rows)


def latency_concurrency_table(
    df: pd.DataFrame,
    workload: str = "cpu",
) -> pd.DataFrame:
    """p95/p99 latency across concurrency levels."""
    rows = []
    for cfg, n_vms in _CONCURRENCY_MAP.items():
        subset = df[(df["config"] == cfg) & (df["workload"] == workload) & (df["metric"] == "p99_latency")]["value"]
        if subset.empty:
            continue
        rows.append(
            {
                "concurrency": n_vms,
                "config": cfg,
                "p95_latency": subset.quantile(0.95) if len(subset) >= 2 else subset.median(),
                "p99_latency": subset.quantile(0.99) if len(subset) >= 2 else subset.median(),
            }
        )
    return pd.DataFrame(rows)


def break_even_concurrency(
    df: pd.DataFrame,
    hourly_rate: float,
    larger_hourly_rate: float,
    monthly_cpu_hours: float = 720.0,
    workload: str = "cpu",
    metric: str = "cpu_seconds_per_job",
) -> int | None:
    """
    Find the concurrency level where upsizing the VM becomes cheaper
    than adding another nested VM.

    Returns the concurrency level (int) or None if nesting is always
    cheaper within the measured range.
    """
    ct = concurrency_table(df, workload, metric, hourly_rate, monthly_cpu_hours)
    if ct.empty:
        return None

    # Direct cost per 1k jobs on the larger instance
    direct_vals = df[
        (df["config"] == "direct")
        & (df["workload"] == workload)
        & (df["metric"] == metric)
    ]["value"]
    if direct_vals.empty:
        return None
    direct_cost = cost_per_1000_jobs(larger_hourly_rate, direct_vals.median(), monthly_cpu_hours)

    for _, row in ct.iterrows():
        if row["cost_per_1000_jobs"] >= direct_cost:
            return int(row["concurrency"])
    return None


# ── Decision logic ───────────────────────────────────────────────────────

Decision = Literal["Keep nesting", "Upsize VM", "Go dedicated"]


def recommend(
    e_capacity: float,
    p_max: float,
    nested_cost_per_1k: float,
    direct_cost_per_1k: float,
    larger_cost_per_1k: float | None = None,
) -> tuple[Decision, str]:
    """
    Return (decision, reason) based on:
      - E_capacity vs P_max threshold
      - Cost comparison
    """
    if e_capacity > p_max:
        if larger_cost_per_1k is not None and larger_cost_per_1k < nested_cost_per_1k:
            return (
                "Upsize VM",
                f"Overhead ({e_capacity:.1%}) exceeds your {p_max:.0%} threshold "
                f"and a larger instance is cheaper per 1 k jobs "
                f"(${larger_cost_per_1k:.2f} vs ${nested_cost_per_1k:.2f}).",
            )
        return (
            "Go dedicated",
            f"Overhead ({e_capacity:.1%}) exceeds your {p_max:.0%} threshold. "
            "Consider dedicated bare-metal or a purpose-built instance.",
        )

    if nested_cost_per_1k <= direct_cost_per_1k:
        return (
            "Keep nesting",
            f"Nested overhead ({e_capacity:.1%}) is within your {p_max:.0%} "
            f"tolerance and nesting is cost-effective "
            f"(${nested_cost_per_1k:.2f} vs ${direct_cost_per_1k:.2f} per 1 k jobs).",
        )

    saving = nested_cost_per_1k - direct_cost_per_1k
    if saving / direct_cost_per_1k < 0.10:
        return (
            "Keep nesting",
            f"Nested overhead ({e_capacity:.1%}) is within tolerance. "
            f"Cost difference is marginal (${saving:.2f} per 1 k jobs).",
        )

    return (
        "Upsize VM",
        f"Overhead ({e_capacity:.1%}) is within tolerance, but nesting is "
        f"${saving:.2f} more per 1 k jobs. A larger direct VM may save money.",
    )


# ── Sensitivity ──────────────────────────────────────────────────────────

def sensitivity_table(
    base_cost: float,
    operational_cost: float = 0.0,
    e_min: float = 0.0,
    e_max: float = 0.60,
    steps: int = 25,
) -> pd.DataFrame:
    """Generate a table of C_nested for varying E_capacity."""
    es = np.linspace(e_min, e_max, steps)
    rows = [
        {
            "E_capacity_pct": round(e * 100, 1),
            "C_nested": round(cost_nested(base_cost, e, operational_cost), 2),
        }
        for e in es
    ]
    return pd.DataFrame(rows)
