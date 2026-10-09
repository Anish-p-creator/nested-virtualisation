"""Methodology page – configs, controlled variables, metrics, limitations, run metadata."""
from __future__ import annotations

import streamlit as st
import pandas as pd


def render(df: pd.DataFrame, is_sample: bool) -> None:
    st.markdown("# 🔬 Methodology")

    if is_sample:
        st.info("Metadata below reflects **synthetic sample data** defaults.", icon="ℹ️")

    # ── Configurations ───────────────────────────────────────────────────
    st.markdown("### Test Configurations")
    st.markdown(
        """
| Config | Description |
|--------|-------------|
| **A – Direct** (`direct`) | Workload runs directly on the L1 (cloud) VM. This is the **baseline**. |
| **B – Nested** (`nested` / `nested-1`) | Workload runs inside a single L2 VM launched on the L1 host via KVM/QEMU. |
| **C – Concurrency** (`nested-2/4/8`) | Multiple L2 VMs run concurrently on the same L1 host to measure contention. |
"""
    )

    # ── Controlled Variables ─────────────────────────────────────────────
    st.markdown("### Controlled Variables")
    st.markdown(
        """
- **vCPUs / RAM**: Identical allocation for direct and each nested VM (inner vCPUs = L1 vCPUs).
- **Kernel version**: Same guest kernel in direct and L2 guests.
- **Disk backend**: `virtio-blk` with identical I/O scheduler.
- **Network**: `virtio-net` with no additional VXLAN / overlay in nested configs.
- **Host tuning**: KSM disabled, THP enabled, `nohz_full` for isolated cores.
- **Warm-up**: Each benchmark preceded by 30 s warm-up; first repeat discarded.
"""
    )

    # ── Metrics ──────────────────────────────────────────────────────────
    st.markdown("### Metrics Collected")
    metrics_data = {
        "Workload": [
            "cpu", "cpu", "cpu",
            "memory", "memory",
            "disk_rand", "disk_rand",
            "disk_seq", "disk_seq",
            "network", "network",
            "redis", "redis",
            "kernel_compile", "kernel_compile",
            "vm_lifecycle", "vm_lifecycle",
        ],
        "Metric": [
            "events_per_sec", "cpu_seconds_per_job", "p99_latency",
            "throughput_MBps", "p99_latency",
            "iops", "p99_latency",
            "throughput_MBps", "p99_latency",
            "throughput_Gbps", "p99_latency",
            "ops_per_sec", "p99_latency",
            "wall_time_sec", "cpu_seconds_per_job",
            "boot_time_sec", "shutdown_time_sec",
        ],
        "Unit": [
            "events/s", "s", "ms",
            "MB/s", "ms",
            "ops/s", "ms",
            "MB/s", "ms",
            "Gbps", "ms",
            "ops/s", "ms",
            "s", "s",
            "s", "s",
        ],
        "Tool": [
            "sysbench cpu", "sysbench cpu", "sysbench cpu",
            "sysbench memory", "sysbench memory",
            "fio randread", "fio randread",
            "fio seqread", "fio seqread",
            "iperf3", "iperf3",
            "redis-benchmark", "redis-benchmark",
            "make -j$(nproc)", "make -j$(nproc)",
            "virsh start / destroy", "virsh start / destroy",
        ],
    }
    st.dataframe(pd.DataFrame(metrics_data), width='stretch', hide_index=True)

    # ── Limitations ──────────────────────────────────────────────────────
    st.markdown("### Limitations")
    st.markdown(
        """
1. **Single host**: All tests run on one instance type; results may differ on other CPU architectures or cloud providers.
2. **No live migration**: Nested VM migration overhead is not measured.
3. **Synthetic workloads**: Real application performance may vary due to caching, scheduling, and I/O patterns.
4. **No GPU/FPGA passthrough**: Only CPU, memory, disk, and network are benchmarked.
5. **Small repeat count**: Statistical significance improves with more repeats; the sample uses 5.
"""
    )

    # ── Expected CSV schema ──────────────────────────────────────────────
    st.markdown("### Expected CSV Schema")
    st.code(
        "config, workload, metric, value, unit, repeat, "
        "cpu_model, kernel, hypervisor_version, vcpus, ram_gb, date",
        language="text",
    )

    # ── Run Metadata ─────────────────────────────────────────────────────
    st.markdown("### Run Metadata")
    if df.empty:
        st.caption("No data loaded.")
        return

    meta_cols = ["cpu_model", "kernel", "hypervisor_version", "vcpus", "ram_gb", "date"]
    available = [c for c in meta_cols if c in df.columns]
    if not available:
        st.caption("No metadata columns found.")
        return

    meta_df = df[available].drop_duplicates().reset_index(drop=True)
    st.dataframe(meta_df, width='stretch', hide_index=True)
