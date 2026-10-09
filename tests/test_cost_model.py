"""Unit tests for app.lib.cost_model – all pure functions, no Streamlit."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.lib.cost_model import (
    capacity_premium,
    cost_nested,
    cost_per_1000_jobs,
    compute_overhead_pct,
    cpu_overhead_pct,
    p99_latency_change_pct,
    e_capacity_from_df,
    concurrency_table,
    latency_concurrency_table,
    break_even_concurrency,
    recommend,
    sensitivity_table,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Minimal tidy dataframe covering the critical paths."""
    rows = []
    meta = dict(
        cpu_model="TestCPU",
        kernel="6.1",
        hypervisor_version="QEMU 8",
        vcpus=8,
        ram_gb=32,
        date="2026-01-01",
    )
    for r in range(1, 4):
        # cpu – events_per_sec  (higher is better)
        rows.append(dict(config="direct", workload="cpu", metric="events_per_sec", value=5000 + r, unit="events/s", repeat=r, **meta))
        rows.append(dict(config="nested", workload="cpu", metric="events_per_sec", value=4400 + r, unit="events/s", repeat=r, **meta))
        # cpu – cpu_seconds_per_job  (lower is better)
        rows.append(dict(config="direct", workload="cpu", metric="cpu_seconds_per_job", value=0.20, unit="s", repeat=r, **meta))
        rows.append(dict(config="nested", workload="cpu", metric="cpu_seconds_per_job", value=0.226, unit="s", repeat=r, **meta))
        rows.append(dict(config="nested-1", workload="cpu", metric="cpu_seconds_per_job", value=0.226, unit="s", repeat=r, **meta))
        rows.append(dict(config="nested-2", workload="cpu", metric="cpu_seconds_per_job", value=0.240, unit="s", repeat=r, **meta))
        rows.append(dict(config="nested-4", workload="cpu", metric="cpu_seconds_per_job", value=0.270, unit="s", repeat=r, **meta))
        rows.append(dict(config="nested-8", workload="cpu", metric="cpu_seconds_per_job", value=0.340, unit="s", repeat=r, **meta))
        # cpu – p99_latency (lower is better)
        rows.append(dict(config="direct", workload="cpu", metric="p99_latency", value=0.45, unit="ms", repeat=r, **meta))
        rows.append(dict(config="nested", workload="cpu", metric="p99_latency", value=0.53, unit="ms", repeat=r, **meta))
        rows.append(dict(config="nested-1", workload="cpu", metric="p99_latency", value=0.53, unit="ms", repeat=r, **meta))
        rows.append(dict(config="nested-2", workload="cpu", metric="p99_latency", value=0.58, unit="ms", repeat=r, **meta))
        rows.append(dict(config="nested-4", workload="cpu", metric="p99_latency", value=0.70, unit="ms", repeat=r, **meta))
        rows.append(dict(config="nested-8", workload="cpu", metric="p99_latency", value=0.95, unit="ms", repeat=r, **meta))
    return pd.DataFrame(rows)


# ── capacity_premium ─────────────────────────────────────────────────────

class TestCapacityPremium:
    def test_basic(self):
        assert capacity_premium(1.13, 1.0) == pytest.approx(0.13, abs=1e-9)

    def test_zero(self):
        assert capacity_premium(1.0, 1.0) == pytest.approx(0.0)

    def test_negative_overhead(self):
        # nested somehow faster – negative premium
        assert capacity_premium(0.9, 1.0) == pytest.approx(-0.1)

    def test_raises_on_zero_direct(self):
        with pytest.raises(ValueError):
            capacity_premium(1.0, 0.0)


# ── cost_nested ──────────────────────────────────────────────────────────

class TestCostNested:
    def test_no_overhead(self):
        assert cost_nested(100, 0.0, 0.0) == pytest.approx(100.0)

    def test_with_overhead(self):
        assert cost_nested(100, 0.15, 10) == pytest.approx(125.0)

    def test_zero_base(self):
        assert cost_nested(0, 0.5, 20) == pytest.approx(20.0)


# ── cost_per_1000_jobs ───────────────────────────────────────────────────

class TestCostPer1000Jobs:
    def test_basic(self):
        # 1 hr rate, 1 CPU-sec/job, 720 CPU-hours/month
        # jobs_per_month = 720*3600/1 = 2_592_000
        # monthly_cost = 1 * 720 = 720
        # cost_per_job = 720 / 2_592_000 ≈ 0.000278
        # cost_per_1000 ≈ 0.278
        result = cost_per_1000_jobs(1.0, 1.0, 720)
        assert result == pytest.approx(0.2778, abs=0.001)

    def test_returns_nan_on_bad_input(self):
        assert math.isnan(cost_per_1000_jobs(1.0, 0.0, 720))
        assert math.isnan(cost_per_1000_jobs(1.0, 1.0, 0.0))


# ── overhead helpers ─────────────────────────────────────────────────────

class TestOverheadHelpers:
    def test_cpu_overhead(self, sample_df):
        oh = cpu_overhead_pct(sample_df)
        assert oh is not None
        # direct ~5001, nested ~4401 → overhead ~12%
        assert 11 < oh < 13

    def test_p99_latency_change(self, sample_df):
        val = p99_latency_change_pct(sample_df)
        assert val is not None
        assert val > 0  # nested has higher latency

    def test_e_capacity(self, sample_df):
        e = e_capacity_from_df(sample_df)
        assert e is not None
        assert e == pytest.approx(0.13, abs=0.01)

    def test_handles_empty_df(self):
        empty = pd.DataFrame(columns=["config", "workload", "metric", "value"])
        assert cpu_overhead_pct(empty) is None
        assert p99_latency_change_pct(empty) is None
        assert e_capacity_from_df(empty) is None


# ── concurrency ──────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrency_table(self, sample_df):
        ct = concurrency_table(sample_df, "cpu", "cpu_seconds_per_job", hourly_rate=0.50)
        assert not ct.empty
        assert list(ct["concurrency"]) == [1, 2, 4, 8]
        # costs should increase with concurrency
        costs = ct["cost_per_1000_jobs"].tolist()
        assert all(costs[i] <= costs[i + 1] for i in range(len(costs) - 1))

    def test_latency_concurrency(self, sample_df):
        lt = latency_concurrency_table(sample_df, "cpu")
        assert not lt.empty
        assert "p99_latency" in lt.columns

    def test_break_even(self, sample_df):
        # With a cheap larger instance the break-even should trigger
        be = break_even_concurrency(sample_df, hourly_rate=0.50, larger_hourly_rate=0.10, monthly_cpu_hours=720)
        # It might be None or an int, but shouldn't crash
        assert be is None or isinstance(be, int)


# ── recommend ────────────────────────────────────────────────────────────

class TestRecommend:
    def test_keep_nesting(self):
        dec, reason = recommend(0.10, 0.25, 1.10, 1.50)
        assert dec == "Keep nesting"

    def test_upsize(self):
        dec, reason = recommend(0.30, 0.20, 1.80, 1.50, 1.40)
        assert dec == "Upsize VM"

    def test_go_dedicated(self):
        dec, reason = recommend(0.50, 0.20, 2.00, 1.50)
        assert dec == "Go dedicated"

    def test_marginal_difference(self):
        dec, reason = recommend(0.05, 0.25, 1.05, 1.00)
        assert dec == "Keep nesting"


# ── sensitivity ──────────────────────────────────────────────────────────

class TestSensitivity:
    def test_table_shape(self):
        s = sensitivity_table(100.0, 10.0, steps=10)
        assert len(s) == 10
        assert s.columns.tolist() == ["E_capacity_pct", "C_nested"]
        # first row should be base + ops (e_cap=0)
        assert s.iloc[0]["C_nested"] == pytest.approx(110.0)

    def test_monotonic(self):
        s = sensitivity_table(100.0)
        costs = s["C_nested"].tolist()
        assert all(costs[i] <= costs[i + 1] for i in range(len(costs) - 1))
