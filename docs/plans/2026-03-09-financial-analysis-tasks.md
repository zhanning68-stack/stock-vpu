# Financial Analysis Module — Module Decomposition & Task Breakdown

**Date**: 2026-03-09
**Spec**: `spec-financial.yaml`
**Design**: `docs/plans/2026-03-09-financial-analysis-design.md`
**Workflow**: SSD+TDD (spec → tests → implementation)

---

## Module Decomposition

### Module 1: `financial_fetcher.py` — Data Layer

**Responsibility**: AKShare data fetching + SQLite storage + cache management

| Function | Description | Complexity |
|----------|-------------|------------|
| `init_db()` | Create SQLite table + index if not exists | Low |
| `_fetch_from_akshare(stock_code, statement_type)` | Call AKShare API for one statement type | Medium |
| `_extract_key_fields(raw_df)` | Map raw AKShare columns to 20 key fields | Medium |
| `_upsert_to_sqlite(stock_code, report_date, payload)` | Insert or update one row | Low |
| `_is_stale(updated_at)` | Check if cached data exceeds TTL (24h) | Low |
| `fetch_financial_data(stock_code, years=5)` | Main entry: SQLite check → AKShare fallback → return DataFrame | High |

**Dependencies**: `sqlite3`, `pandas`, `akshare`, `json`, `datetime`
**Test count estimate**: ~15 tests (6 functions × 2-3 cases each)

### Module 2: `financial_analyzer.py` — Analysis Engine

**Responsibility**: Circuit breaker fraud detection + health profiling

| Function | Description | Complexity |
|----------|-------------|------------|
| `_test_interest_anomaly(df)` | Test 1: implied yield check | Low |
| `_test_revenue_receivable_divergence(df)` | Test 2: AR vs revenue growth | Medium |
| `_test_high_cash_high_debt(df)` | Test 3: cash+debt ratio check | Medium |
| `fraud_scan(df)` | Run all 3 tests, return circuit breaker result | Medium |
| `_dupont_analysis(df)` | ROE decomposition into 3 factors | Low |
| `_cash_flow_quality(df)` | OCF/net profit ratio + quality label | Low |
| `health_profile(df)` | Run DuPont + cash flow quality | Low |
| `analyze(stock_code)` | Full pipeline: fetch → scan → profile (if passed) | High |

**Dependencies**: `pandas`, `financial_fetcher`
**Test count estimate**: ~25 tests (from spec-financial.yaml test cases)

### Module 3: `workUI.html` — UI Update

**Responsibility**: Add tab switching + financial analysis card with two states

| Component | Description | Complexity |
|-----------|-------------|------------|
| Tab system | Two pill buttons, JS toggle content divs | Low |
| Fraud scan cards | 3 audit test cards with left-border color | Medium |
| Gate banner | Pass/fail binary banner | Low |
| Health section (pass) | DuPont metrics + OCF ratio display | Medium |
| Locked section (fail) | Grayed out health area with lock icon | Low |
| Demo toggle | Hidden button to switch mock states | Low |
| Mock data | Two JSON objects (pass + fail states) | Low |

**Dependencies**: Tailwind CSS, vanilla JS
**No Python dependencies**

### Module 4: `test_financial.py` — Test Suite

**Responsibility**: Unit + integration tests for modules 1 & 2

| Test Class | Tests | Coverage Target |
|-----------|-------|-----------------|
| `TestInterestAnomaly` | 5 tests | `_test_interest_anomaly` |
| `TestRevenueReceivableDivergence` | 6 tests | `_test_revenue_receivable_divergence` |
| `TestHighCashHighDebt` | 4 tests | `_test_high_cash_high_debt` |
| `TestCircuitBreaker` | 3 tests | `fraud_scan` |
| `TestDuPontAnalysis` | 3 tests | `_dupont_analysis` |
| `TestCashFlowQuality` | 6 tests | `_cash_flow_quality` |
| `TestFinancialFetcher` | 8 tests | `financial_fetcher.py` |
| `TestAnalyzeIntegration` | 5 tests | `analyze` end-to-end |

**Total**: ~40 tests

---

## Task Breakdown (Execution Order)

Following SSD+TDD: spec (done) → tests → implementation

### Phase 1: Tests First (TDD Red Phase)

| Task | Module | Description | Estimate | Dependency |
|------|--------|-------------|----------|------------|
| T1 | test_financial.py | Write `TestInterestAnomaly` (5 tests) | 15 min | spec-financial.yaml |
| T2 | test_financial.py | Write `TestRevenueReceivableDivergence` (6 tests) | 20 min | spec-financial.yaml |
| T3 | test_financial.py | Write `TestHighCashHighDebt` (4 tests) | 15 min | spec-financial.yaml |
| T4 | test_financial.py | Write `TestCircuitBreaker` (3 tests) | 10 min | T1, T2, T3 |
| T5 | test_financial.py | Write `TestDuPontAnalysis` (3 tests) | 10 min | spec-financial.yaml |
| T6 | test_financial.py | Write `TestCashFlowQuality` (6 tests) | 15 min | spec-financial.yaml |
| T7 | test_financial.py | Write `TestFinancialFetcher` (8 tests) | 25 min | spec-financial.yaml |
| T8 | test_financial.py | Write `TestAnalyzeIntegration` (5 tests) | 20 min | T4, T5, T6, T7 |

**Phase 1 subtotal**: ~40 tests, ~2.2 hours

### Phase 2: Implementation (TDD Green Phase)

| Task | Module | Description | Estimate | Dependency |
|------|--------|-------------|----------|------------|
| T9 | financial_analyzer.py | Implement `_test_interest_anomaly` | 20 min | T1 (tests exist) |
| T10 | financial_analyzer.py | Implement `_test_revenue_receivable_divergence` | 30 min | T2 |
| T11 | financial_analyzer.py | Implement `_test_high_cash_high_debt` | 25 min | T3 |
| T12 | financial_analyzer.py | Implement `fraud_scan` (orchestrator) | 15 min | T9, T10, T11 |
| T13 | financial_analyzer.py | Implement `_dupont_analysis` | 15 min | T5 |
| T14 | financial_analyzer.py | Implement `_cash_flow_quality` | 15 min | T6 |
| T15 | financial_analyzer.py | Implement `health_profile` | 10 min | T13, T14 |
| T16 | financial_fetcher.py | Implement `init_db` + `_upsert_to_sqlite` | 20 min | T7 |
| T17 | financial_fetcher.py | Implement `_fetch_from_akshare` + `_extract_key_fields` | 40 min | T7 |
| T18 | financial_fetcher.py | Implement `fetch_financial_data` (cache orchestrator) | 25 min | T16, T17 |
| T19 | financial_analyzer.py | Implement `analyze` (full pipeline) | 15 min | T12, T15, T18 |

**Phase 2 subtotal**: ~3.8 hours

### Phase 3: UI Update

| Task | Module | Description | Estimate | Dependency |
|------|--------|-------------|----------|------------|
| T20 | workUI.html | Add tab switching system (VPU / Financial) | 30 min | None |
| T21 | workUI.html | Build fraud scan cards (3 test cards + gate banner) | 45 min | T20 |
| T22 | workUI.html | Build health section (DuPont + OCF) | 30 min | T21 |
| T23 | workUI.html | Add demo toggle + mock data (pass/fail states) | 20 min | T21, T22 |

**Phase 3 subtotal**: ~2 hours

### Phase 4: Integration & Review

| Task | Module | Description | Estimate | Dependency |
|------|--------|-------------|----------|------------|
| T24 | all | Run full test suite, fix failures | 30 min | T19 |
| T25 | all | Ruff lint + mypy check on new modules | 15 min | T24 |
| T26 | all | Code review (self or oracle) | 20 min | T25 |

**Phase 4 subtotal**: ~1 hour

---

## Task Assignment Strategy

### Parallelizable Groups

The following tasks can run in parallel:

**Group A** (independent fraud tests): T1, T2, T3 → T9, T10, T11
**Group B** (independent health tests): T5, T6 → T13, T14
**Group C** (data layer): T7 → T16, T17, T18
**Group D** (UI): T20, T21, T22, T23

### Recommended Agent Delegation

| Task Group | Agent Category | Skills | Reason |
|-----------|---------------|--------|--------|
| T1-T8 (tests) | `testing` | `superpowers/test-driven-development` | TDD red phase |
| T9-T15 (analyzer) | `deep` | `superpowers/test-driven-development` | Core business logic with edge cases |
| T16-T19 (fetcher) | `unspecified-high` | `superpowers/test-driven-development` | Data layer with AKShare + SQLite |
| T20-T23 (UI) | `visual-engineering` | `frontend-ui-ux` | HTML/CSS/JS UI work |
| T24-T26 (review) | `quick` | `superpowers/verification-before-completion` | Lint + test verification |

### Sequential Execution (if not parallelizing)

Recommended order: T1-T8 → T9-T19 → T20-T23 → T24-T26

With user confirmation gates after each phase:
1. After Phase 1 (tests): "40 tests written, all red. Proceed to implementation?"
2. After Phase 2 (implementation): "All tests green. Proceed to UI?"
3. After Phase 3 (UI): "UI updated. Run final review?"

---

## Total Estimate

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1: Tests | T1-T8 | ~2.2 hours |
| Phase 2: Implementation | T9-T19 | ~3.8 hours |
| Phase 3: UI | T20-T23 | ~2.0 hours |
| Phase 4: Review | T24-T26 | ~1.0 hour |
| **Total** | **26 tasks** | **~9 hours** |

With parallelization (Groups A+B+C simultaneously): **~5-6 hours**

---

## Acceptance Criteria

- [ ] All 40 tests pass (`pytest test_financial.py -v`)
- [ ] `ruff check financial_analyzer.py financial_fetcher.py` — 0 errors
- [ ] `fraud_scan()` correctly halts on any single test failure
- [ ] `health_profile()` only runs when all 3 fraud tests pass
- [ ] SQLite database auto-creates on first use
- [ ] UI tab switching works in browser
- [ ] UI shows both pass and fail states via demo toggle
- [ ] Edge cases handled (zero division, missing data, negative values)
