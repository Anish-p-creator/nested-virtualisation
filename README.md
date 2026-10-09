# Nested Virtualization Cost Explorer

A Streamlit dashboard that visualises benchmark results comparing **direct cloud VMs** against **nested (L2) VMs** and translates the performance overhead into cloud cost per unit of useful work.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-%E2%89%A51.30-red)
![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen)

---

## Quick Start

```bash
# 1. Clone / copy the project
cd nested-virt-cost-explorer

# 2. Create a virtual-env (recommended)
python -m venv .venv && .venv\Scripts\activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app/main.py
```

The app opens at **http://localhost:8501**.  
If no real data exists in `data/processed/`, synthetic sample data is loaded automatically and a warning banner is shown.

---

## Pages

| Page | What it shows |
|------|---------------|
| **Overview** | KPI cards (CPU overhead %, p99 latency change, capacity premium, cost per 1k jobs) and a plain-English summary. |
| **Benchmarks** | Grouped bar charts (direct vs nested) with median + error bars, organized in tabs (CPU, Memory, Disk, Network, Latency). Filter by workload and repeat. |
| **Concurrency** | Cost per job and p95/p99 latency vs concurrent L2 VMs (1→8). Break-even point highlighted. |
| **Cost Calculator** | Interactive pricing inputs, P_max slider, recommendation badge (Keep nesting / Upsize VM / Go dedicated), sensitivity chart, downloadable CSV. |
| **Methodology** | Configs A/B/C, controlled variables, metrics table, limitations, CSV schema, and run metadata. |

---

## Expected CSV Schema

Place one or more CSV files in `data/processed/`. Each row = one benchmark run.

```
config, workload, metric, value, unit, repeat,
cpu_model, kernel, hypervisor_version, vcpus, ram_gb, date
```

| Column | Values |
|--------|--------|
| `config` | `direct`, `nested`, `nested-1`, `nested-2`, `nested-4`, `nested-8` |
| `workload` | `cpu`, `memory`, `disk_rand`, `disk_seq`, `network`, `redis`, `kernel_compile`, `vm_lifecycle` |
| `metric` | Free text (e.g. `events_per_sec`, `p99_latency`, `iops`, …) |
| `value` | Numeric |
| `unit` | Free text (`events/s`, `ms`, `MB/s`, …) |
| `repeat` | Integer run number |
| `cpu_model` | String |
| `kernel` | String |
| `hypervisor_version` | String |
| `vcpus` | Integer |
| `ram_gb` | Integer |
| `date` | ISO date string |

### Swapping in Real Data

1. Drop your CSVs into `data/processed/`.
2. Re-launch or refresh the app – the sample banner disappears automatically.
3. Alternatively, use the **Upload** widget in the sidebar for ad-hoc analysis.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

All cost-model functions are pure (no Streamlit dependency) and tested independently.

---

## Project Structure

```
nested-virt-cost-explorer/
├── app/
│   ├── main.py              # Streamlit entry point
│   ├── pages/
│   │   ├── overview.py
│   │   ├── benchmarks.py
│   │   ├── concurrency.py
│   │   ├── cost_calculator.py
│   │   └── methodology.py
│   └── lib/
│       ├── data_loader.py   # CSV loading + sample generation
│       ├── cost_model.py    # Pure cost functions (unit-tested)
│       └── charts.py        # Plotly figure builders
├── tests/
│   └── test_cost_model.py   # pytest suite (22 tests)
├── data/
│   ├── processed/           # Place real CSVs here
│   └── sample/              # Auto-generated synthetic data
├── requirements.txt
└── README.md
```

---

## License

MIT
