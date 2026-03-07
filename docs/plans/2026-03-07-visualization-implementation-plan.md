# Streamlit Daily Monitoring Visualization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a Streamlit daily-monitoring view for VPU/APU with clear KPIs, charts, and CSV export.

**Architecture:** Streamlit (`app.py`) remains the single UI entrypoint. Data flows from `fetch_5min_kline` to `calculate_vpu`, then into `visualizer.render_chart` / `render_apu_chart`. Session state keeps the latest results for re-rendering and export.

**Tech Stack:** Python, Streamlit, Pandas, streamlit-echarts, Matplotlib (PNG export via CLI).

---

### Task 1: Add a concise daily-monitoring hint in the UI

**Files:**
- Modify: `app.py` (near the title block)

**Step 1: Write the failing test**

No automated UI test is currently in place for Streamlit. Skip TDD here and validate manually.

**Step 2: Implement minimal UI copy**

Add a short `st.caption(...)` below the title to clarify the daily monitoring intent and primary actions.

**Step 3: Manual verification**

Run: `streamlit run app.py`

Expected:
- Page shows a short caption under the title describing daily monitoring.
- Sidebar inputs and “获取数据并计算” remain unchanged.

**Step 4: Commit**

```bash
git add app.py
git commit -m "docs: add daily monitoring caption"
```

---

### Task 2: Validate error paths and empty-state messaging

**Files:**
- Modify: `app.py` (error handling messages if needed)

**Step 1: Write the failing test**

No automated test for Streamlit error display. Validate manually.

**Step 2: Manual verification**

Run: `streamlit run app.py`

Checks:
- Invalid date range shows an error and no charts.
- Empty data shows a clear error and no stale charts.
- Runtime error shows a clear message and resets session state.

**Step 3: Commit**

```bash
git add app.py
git commit -m "fix: clarify streamlit error messages"
```

---

### Task 3: Verify charts and CSV export

**Files:**
- No code changes expected

**Step 1: Manual verification**

Run: `streamlit run app.py`

Checks:
- KPI metrics display for a valid stock code.
- VPU and APU tabs render charts.
- CSV export downloads the computed daily results.

**Step 2: Commit**

No commit required unless changes were made.
