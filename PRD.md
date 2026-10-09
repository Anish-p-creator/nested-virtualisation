# Product Requirements Document (PRD)
**Project Name:** Nested Virtualization Cost Explorer
**Document Version:** 1.0
**Date:** October 9, 2026

---

## 1. Executive Summary
The **Nested Virtualization Cost Explorer** is an interactive, web-based dashboard designed to help cloud architects, DevOps engineers, and FinOps practitioners analyze the performance and financial overhead of running nested virtualization (L2 VMs) inside cloud instances (L1 VMs). It bridges the gap between raw technical benchmarks and financial cost, offering clear recommendations on whether an organization should keep nesting, upsize their instances, or pivot to dedicated bare-metal servers.

## 2. Target Audience
* **Cloud Infrastructure Engineers:** Looking to quantify CPU and latency penalties introduced by a second virtualization layer.
* **FinOps / Financial Planners:** Looking to understand how performance degradation translates into a "hidden capacity tax" on monthly cloud bills.

## 3. Core Capabilities & User Flow

The application provides a robust navigation sidebar with 5 primary pages:

### 3.1. Overview Page
* **Goal:** High-level executive summary of the benchmark metrics.
* **Features:**
  * 4 Dynamic KPI Cards: CPU Overhead %, P99 Latency Change, Capacity Premium ($E_{capacity}$), and Direct vs Nested Cost per 1,000 jobs.
  * Auto-generated, plain-English summary explaining the impact of the data.

### 3.2. Benchmarks Page
* **Goal:** Detailed visualization of raw performance data.
* **Features:**
  * Grouped bar charts built in Plotly comparing Direct vs. Nested performance across categories (CPU, Memory, Disk, Network, Latency).
  * Median values plotted with P5 to P95 error bars.
  * Interactive multi-select filters for workloads and repeat runs.
  * Expandable tabular views of raw statistical aggregations (min, max, mean, median, standard dev).

### 3.3. Concurrency Scaling
* **Goal:** Understand contention when packing multiple L2 VMs on a single host.
* **Features:**
  * Line charts graphing cost and tail latency against the number of concurrent VMs (1, 2, 4, 8).
  * Automated "Break-even" detection algorithm that visually highlights the point at which upsizing to a larger instance becomes financially optimal over adding more nested VMs.

### 3.4. Cost Calculator (Interactive)
* **Goal:** Interactive "What-If" financial modeling.
* **Features:**
  * Dynamic sidebar inputs for instance pricing (Base and Larger instance), capacity multipliers, monthly CPU hours, and operational overhead.
  * A slider to set the user's $P_{max}$ (Maximum Acceptable Overhead).
  * **Recommendation Engine:** Calculates costs and issues a dynamic glowing badge:
    * **Keep Nesting** (Triggers celebratory balloons animation)
    * **Upsize VM**
    * **Go Dedicated** (Triggers snow animation)
  * Sensitivity analysis line chart mapping cost against hypothetical capacity premiums (0% to 60%).
  * Downloadable CSV export of the calculation results.

### 3.5. Methodology
* **Goal:** Transparency into how benchmarks were conducted.
* **Features:**
  * Markdown tables outlining Configs (A/B/C), controlled variables, and collected metrics.
  * Display of the expected CSV data schema.
  * Automated extraction and display of metadata (CPU model, Kernel, Hypervisor version) directly from the uploaded dataset.

## 4. Technical Specifications

### 4.1. Tech Stack
* **Language:** Python 3.11+
* **Framework:** Streamlit ($\ge$ 1.30.0)
* **Data Processing:** Pandas, NumPy
* **Data Visualization:** Plotly
* **Testing:** Pytest

### 4.2. Data Model & Ingestion
* **Ingestion Method:** Automated loading from the local `data/processed/` directory. Falls back to generating a synthetic mock dataset if no CSV is found. Also supports ad-hoc CSV uploads via the sidebar.
* **Schema Requirement:** Tidy CSV format. Required columns include:
  `config`, `workload`, `metric`, `value`, `unit`, `repeat`, `cpu_model`, `kernel`, `hypervisor_version`, `vcpus`, `ram_gb`, `date`.

### 4.3. Business Logic Architecture
* The application enforces strict separation of concerns. 
* All mathematical modeling (capacity premium, cost formulas, overhead logic, break-even concurrency) is isolated in `app/lib/cost_model.py`.
* The core logic contains exclusively pure functions and boasts 100% test coverage (22 passing unit tests).

## 5. UI/UX & Aesthetics
* **Theme:** Enforced Dark Mode (`#0E1117` base).
* **Styling paradigm:** Premium Glassmorphism. KPI cards utilize `backdrop-filter` blurring, subtle translucent borders, and smooth drop shadows.
* **Color Palette:**
  * Direct Data: Blue (`#4A90D9`)
  * Nested Data: Orange (`#E8883C`)
* **Typography:** Inter font family, utilizing heavy weights for headers and transparent gradient text clipping for primary metrics to provide a sleek, modern feel.
* **Micro-interactions:** Cards elegantly scale and raise (`translateY(-6px)`) on hover. Recommendation badges feature pulsating neon drop-shadows.

## 6. Future Considerations (V2)
* Support for uploading and overlaying multiple CSV files to compare different hardware architectures (e.g., AMD vs Intel vs ARM) simultaneously.
* API integration to pull live pricing data from AWS/GCP/Azure rather than relying on manual numerical input.
