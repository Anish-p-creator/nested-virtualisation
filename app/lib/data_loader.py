"""
Generate synthetic benchmark CSVs and load real / sample data.

No Streamlit imports – this module is pure Python.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

# ── Column schema ────────────────────────────────────────────────────────
EXPECTED_COLUMNS = [
    "config",
    "workload",
    "metric",
    "value",
    "unit",
    "repeat",
    "cpu_model",
    "kernel",
    "hypervisor_version",
    "vcpus",
    "ram_gb",
    "date",
]

VALID_CONFIGS = {"direct", "nested", "nested-1", "nested-2", "nested-4", "nested-8"}

VALID_WORKLOADS = {
    "cpu",
    "memory",
    "disk_rand",
    "disk_seq",
    "network",
    "redis",
    "kernel_compile",
    "vm_lifecycle",
}


# ── Paths ────────────────────────────────────────────────────────────────
def _project_root() -> Path:
    """Return the project root (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent.parent


def processed_dir() -> Path:
    return _project_root() / "data" / "processed"


def sample_dir() -> Path:
    return _project_root() / "data" / "sample"


# ── Synthetic data generator ─────────────────────────────────────────────
_RNG = np.random.default_rng(42)

_WORKLOAD_TEMPLATES: dict[str, list[dict]] = {
    "cpu": [
        {"metric": "events_per_sec", "unit": "events/s", "direct_mean": 4800, "overhead": 0.12},
        {"metric": "cpu_seconds_per_job", "unit": "s", "direct_mean": 0.21, "overhead": 0.13},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 0.45, "overhead": 0.18},
    ],
    "memory": [
        {"metric": "throughput_MBps", "unit": "MB/s", "direct_mean": 12500, "overhead": 0.05},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 0.12, "overhead": 0.08},
    ],
    "disk_rand": [
        {"metric": "iops", "unit": "ops/s", "direct_mean": 48000, "overhead": 0.15},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 0.90, "overhead": 0.22},
    ],
    "disk_seq": [
        {"metric": "throughput_MBps", "unit": "MB/s", "direct_mean": 1800, "overhead": 0.08},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 1.2, "overhead": 0.10},
    ],
    "network": [
        {"metric": "throughput_Gbps", "unit": "Gbps", "direct_mean": 9.2, "overhead": 0.06},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 0.35, "overhead": 0.30},
    ],
    "redis": [
        {"metric": "ops_per_sec", "unit": "ops/s", "direct_mean": 125000, "overhead": 0.10},
        {"metric": "p99_latency", "unit": "ms", "direct_mean": 0.55, "overhead": 0.20},
    ],
    "kernel_compile": [
        {"metric": "wall_time_sec", "unit": "s", "direct_mean": 180, "overhead": 0.14},
        {"metric": "cpu_seconds_per_job", "unit": "s", "direct_mean": 680, "overhead": 0.14},
    ],
    "vm_lifecycle": [
        {"metric": "boot_time_sec", "unit": "s", "direct_mean": 3.5, "overhead": 0.45},
        {"metric": "shutdown_time_sec", "unit": "s", "direct_mean": 1.2, "overhead": 0.25},
    ],
}

# Concurrency scaling factors (overhead multiplier relative to nested-1)
_CONCURRENCY_SCALE = {
    "nested-1": 1.0,
    "nested-2": 1.18,
    "nested-4": 1.42,
    "nested-8": 1.85,
}

_META = {
    "cpu_model": "Intel Xeon Platinum 8375C",
    "kernel": "6.1.0-22-cloud-amd64",
    "hypervisor_version": "QEMU 8.2.2 / KVM",
    "vcpus": 8,
    "ram_gb": 32,
    "date": "2026-09-15",
}


def generate_sample_data(
    repeats: int = 5,
    dest: Path | None = None,
) -> pd.DataFrame:
    """Create a synthetic benchmark dataset and optionally save it."""
    rows: list[dict] = []
    for workload, templates in _WORKLOAD_TEMPLATES.items():
        for tmpl in templates:
            for r in range(1, repeats + 1):
                # direct
                noise = _RNG.normal(0, 0.02)
                direct_val = tmpl["direct_mean"] * (1 + noise)
                rows.append(
                    {
                        "config": "direct",
                        "workload": workload,
                        "metric": tmpl["metric"],
                        "value": round(direct_val, 6),
                        "unit": tmpl["unit"],
                        "repeat": r,
                        **_META,
                    }
                )
                # nested (alias for nested-1)
                nested_noise = _RNG.normal(0, 0.03)
                # For metrics where higher is better (throughput), nested is lower
                # For metrics where lower is better (latency, time), nested is higher
                is_lower_better = any(
                    kw in tmpl["metric"]
                    for kw in ("latency", "time", "seconds")
                )
                if is_lower_better:
                    nested_val = direct_val * (1 + tmpl["overhead"] + nested_noise)
                else:
                    nested_val = direct_val * (1 - tmpl["overhead"] + nested_noise)
                rows.append(
                    {
                        "config": "nested",
                        "workload": workload,
                        "metric": tmpl["metric"],
                        "value": round(nested_val, 6),
                        "unit": tmpl["unit"],
                        "repeat": r,
                        **_META,
                    }
                )
                # concurrency configs
                for cfg, scale in _CONCURRENCY_SCALE.items():
                    conc_noise = _RNG.normal(0, 0.03)
                    if is_lower_better:
                        conc_val = direct_val * (1 + tmpl["overhead"] * scale + conc_noise)
                    else:
                        conc_val = direct_val * (1 - tmpl["overhead"] * scale + conc_noise)
                    rows.append(
                        {
                            "config": cfg,
                            "workload": workload,
                            "metric": tmpl["metric"],
                            "value": round(conc_val, 6),
                            "unit": tmpl["unit"],
                            "repeat": r,
                            **_META,
                        }
                    )

    df = pd.DataFrame(rows)
    if dest is not None:
        dest.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest / "benchmarks.csv", index=False)
    return df


# ── Validation ───────────────────────────────────────────────────────────
def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Return a list of validation error strings (empty == valid)."""
    errors: list[str] = []
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
    extra = set(df.columns) - set(EXPECTED_COLUMNS)
    if extra:
        errors.append(f"Unexpected columns (ignored): {sorted(extra)}")
    if df.empty:
        errors.append("DataFrame is empty.")
    if "config" in df.columns:
        bad = set(df["config"].dropna().unique()) - VALID_CONFIGS
        if bad:
            errors.append(f"Unknown config values: {sorted(bad)}")
    if "value" in df.columns:
        non_numeric = df["value"].apply(lambda v: not isinstance(v, (int, float, np.integer, np.floating)))
        if non_numeric.any():
            errors.append(f"{non_numeric.sum()} non-numeric value(s) found.")
    return errors


# ── Loading ──────────────────────────────────────────────────────────────
def load_data(uploaded_file=None) -> Tuple[pd.DataFrame, bool]:
    """
    Load benchmark data, returning (dataframe, is_sample).

    Priority:
      1. uploaded_file (bytes-like from Streamlit)
      2. data/processed/*.csv
      3. data/sample/*.csv  (auto-generated if missing)
    """
    # 1. Uploaded
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        return df, False

    # 2. Real data
    pdir = processed_dir()
    if pdir.exists():
        csvs = list(pdir.glob("*.csv"))
        if csvs:
            dfs = [pd.read_csv(f) for f in csvs]
            return pd.concat(dfs, ignore_index=True), False

    # 3. Sample
    sdir = sample_dir()
    csv_path = sdir / "benchmarks.csv"
    if not csv_path.exists():
        generate_sample_data(dest=sdir)
    df = pd.read_csv(csv_path)
    return df, True
