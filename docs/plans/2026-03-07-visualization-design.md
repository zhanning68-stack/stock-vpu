# Visualization Design — Daily Monitoring (Streamlit)

## Goals
- Provide a fast, single-screen daily monitoring view for VPU/APU indicators.
- Keep the interaction simple: input parameters → fetch → compute → view charts.
- Allow quick export of computed daily results as CSV.

## Non-Goals
- Deep research tooling (comparisons across many tickers, annotations, advanced filters).
- New data sources or indicator definitions.

## Selected Approach
**Daily Monitoring Dashboard (Recommended)**: a minimal Streamlit layout with KPI metrics, two chart tabs (VPU/APU), and CSV export. This aligns with the daily monitoring goal and leverages existing `app.py` and `visualizer.py` behavior.

## Architecture
- **Entry point**: `app.py` Streamlit app.
- **Data pipeline**: `fetch_5min_kline` → `calculate_vpu` → `visualizer.render_chart` / `render_apu_chart`.
- **State**: `st.session_state` holds the last computed `result_df` and `stock_code` for consistent re-rendering and export.

## Components
- **Sidebar inputs**: stock code, date range, price/trim parameters, and “Fetch & Calculate”.
- **Top KPI row**: Average VPU, VPU_Up, VPU_Down.
- **Main charts**: tabs for VPU indicator and APU indicator (ECharts).
- **Actions**: CSV download for computed daily data.

## Data Flow
1. User configures inputs in sidebar.
2. Fetch 5-minute data for the requested range.
3. Calculate daily indicators (VPU/APU/MA5/close price).
4. Store results in session state.
5. Render KPI metrics and charts.
6. Export CSV from computed daily data.

## Error Handling
- Validate stock code and date range before fetch.
- If fetch returns empty data, show error and clear cached results.
- If calculation yields empty results, show error and clear cached results.
- Catch runtime exceptions and show a readable error message.

## Testing & Verification
- Keep existing visualizer structure tests in `test_vpu.py` as baseline.
- Manual UI sanity check: `streamlit run app.py` and verify KPIs + charts render for a known stock code.
- Validate empty-data and error paths show clear messages and do not render stale results.

## Risks & Mitigations
- **Data gaps or API failures**: handled by empty-data and exception paths in UI.
- **UI confusion**: daily monitoring layout avoids deep nesting and keeps core actions visible.
