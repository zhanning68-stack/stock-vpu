# Streamlit Visualization Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the Streamlit visualization code to improve performance via `st.cache_data`, better separate concerns by moving ECharts JS wrapping to `visualizer.py`, and update the project's design document.

**Architecture:** Use `@st.cache_data` to memoize the data fetching and computation steps, significantly reducing redundant AKShare API calls. Move all ECharts-specific rendering logic (`wrap_js_code`) from the UI layer (`app.py`) to the presentation layer (`visualizer.py`). Update `stock-vpu-design.md` to reflect these structural changes and the transition to the new UI paradigm.

**Tech Stack:** Python, Streamlit (`@st.cache_data`), Pandas, ECharts.

---

### Task 1: Migrate `wrap_js_code` to visualizer.py

**Files:**
- Modify: `visualizer.py`
- Modify: `app.py`
- Test: `test_vpu.py`

**Step 1: Write the failing test**

In `test_vpu.py`, add a test to verify `wrap_js_code` exists and works inside `visualizer.py`.

```python
def test_wrap_js_code_in_visualizer():
    from visualizer import wrap_js_code
    from streamlit_echarts import JsCode
    
    test_dict = {"formatter": "function(params) { return 'test'; }"}
    wrapped = wrap_js_code(test_dict)
    
    assert "formatter" in wrapped
    assert isinstance(wrapped["formatter"], JsCode)
    assert wrapped["formatter"].js_code == "function(params) { return 'test'; }"
```

**Step 2: Run test to verify it fails**

Run: `pytest test_vpu.py::test_wrap_js_code_in_visualizer -v`
Expected: FAIL with "ImportError: cannot import name 'wrap_js_code'"

**Step 3: Write minimal implementation**

Move the `wrap_js_code` function from `app.py` to `visualizer.py`. Add the necessary import `from streamlit_echarts import JsCode` to `visualizer.py`. Remove it from `app.py` and import it instead: `from visualizer import render_chart, render_apu_chart, wrap_js_code`.

**Step 4: Run test to verify it passes**

Run: `pytest test_vpu.py::test_wrap_js_code_in_visualizer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py visualizer.py test_vpu.py
git commit -m "refactor: move wrap_js_code to visualizer module"
```

---

### Task 2: Implement data caching in app.py

**Files:**
- Modify: `app.py`

**Step 1: Write the failing test**

Skip automated tests for Streamlit caching behavior as it requires a full app context. Manual verification will be used.

**Step 2: Write minimal implementation**

In `app.py`, extract the data fetching and computation logic into a new cached function:

```python
@st.cache_data(ttl=3600, show_spinner="Fetching and computing data...")
def load_and_compute_data(code: str, start: str, end: str, cfg_dict: dict) -> pd.DataFrame:
    from data_fetcher import fetch_5min_kline
    from calculator import calculate_vpu
    from config import Config
    
    # Reconstruct Config from dict for caching serialization
    cfg = Config(**cfg_dict)
    
    raw_df = fetch_5min_kline(code, start, end)
    if raw_df.empty:
        return pd.DataFrame()
        
    result_df = calculate_vpu(raw_df, cfg, code=code)
    return result_df
```

Replace the inline `fetch_5min_kline` and `calculate_vpu` calls in the `if fetch_button:` block with a call to this new function. Pass `cfg.__dict__` to allow Streamlit to hash the arguments correctly. Update the UI to render based on the returned DataFrame instead of relying heavily on manual `st.session_state` management.

**Step 3: Run manual test to verify it passes**

Run: `python3 -m streamlit run app.py`
Expected: 
1. The app loads and fetches data successfully. 
2. Changing a parameter and clicking fetch triggers a re-compute.
3. Clicking fetch with the *same* parameters returns instantly (cached).

**Step 4: Commit**

```bash
git add app.py
git commit -m "perf: add st.cache_data for data fetching and computation"
```

---

### Task 3: Update design documentation

**Files:**
- Create/Modify: `stock-vpu-design.md`

**Step 1: Write minimal implementation**

Update `stock-vpu-design.md` (or create it if it doesn't exist in the root) to reflect the new architecture:

```markdown
# VPU Liquidity Depth Visualization Design

## Architecture
The visualization layer is built on Streamlit (`app.py`), acting as the primary entry point. 
It utilizes a dual-engine rendering approach:
- **Interactive Web**: `streamlit-echarts` for dynamic, zoomable browser charts.
- **Static Export**: `matplotlib` for generating high-quality PNG reports via CLI (`main.py`).

## Core Principles
1. **Performance**: Heavy API calls to AKShare and subsequent Pandas computations are memoized using `@st.cache_data(ttl=3600)`. This reduces network latency and prevents API rate limits (IP bans).
2. **Separation of Concerns**: `app.py` handles only UI layout and state routing. All chart-specific configurations, including the JavaScript injection (`wrap_js_code`) for ECharts tooltips, are strictly encapsulated within `visualizer.py`.
3. **Robustness**: The UI gracefully handles empty data states, invalid inputs, and API exceptions without leaving stale visual artifacts.

## Visual Semantics
- **VPU_Up (抛压)**: Displayed in Red (`#eb5454`). Represents volume during price increases.
- **VPU_Down (支撑)**: Displayed in Green (`#47b262`). Represents volume during price decreases, plotted on the negative Y-axis for comparative visual weight but absolute-value formatted in tooltips via injected JS.
```

**Step 2: Commit**

```bash
git add stock-vpu-design.md
git commit -m "docs: update design doc with new visualization architecture"
```
