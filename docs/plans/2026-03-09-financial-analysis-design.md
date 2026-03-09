# Financial Analysis Module — System Design

**Date**: 2026-03-09
**Status**: Approved
**Approach**: Plan A — Unified card with internal tab switching

---

## 1. Overview

Extend Stock VPU from a single-dimension liquidity analysis tool into a dual-analysis platform:

- **VPU Analysis** (existing): Volume-per-price-unit liquidity depth analysis
- **Financial Analysis** (new): Circuit breaker fraud detection + health profiling

The two analyses share the same stock context (code, date range) and are accessed via horizontal tab switching within the workspace UI.

---

## 2. Core Design: Circuit Breaker Pattern

The financial analysis module uses a **serial funnel** (not parallel multi-dimension):

```
Step 1: Fraud Red Flag Scan (MANDATORY)
    ├── PASS all 3 tests → Step 2
    └── FAIL any test    → HALT (no Step 2)

Step 2: Health Profile (CONDITIONAL)
    ├── DuPont Analysis (ROE decomposition)
    └── Cash Flow Quality (OCF / Net Profit)
```

**Why serial, not parallel**: A company with fabricated financials produces meaningless ROE/OCF numbers. Running health metrics on fraudulent data wastes compute and misleads users. The circuit breaker ensures downstream analysis only runs on trustworthy data.

---

## 3. Data Architecture

### 3.1 Data Source

Standard financial statements (三表) from AKShare:
- Balance Sheet (资产负债表)
- Income Statement (利润表)
- Cash Flow Statement (现金流量表)

### 3.2 Key Fields (20 compressed fields)

| # | Field | Chinese Name | Source Statement | Used By |
|---|-------|-------------|------------------|---------|
| 1 | `monetary_funds` | 货币资金 | Balance Sheet | Fraud Test 1, 3 |
| 2 | `interest_income` | 利息收入 | Income Statement | Fraud Test 1 |
| 3 | `interest_expense` | 利息支出 | Income Statement | Fraud Test 3 |
| 4 | `accounts_receivable` | 应收账款 | Balance Sheet | Fraud Test 2 |
| 5 | `revenue` | 营业收入 | Income Statement | Fraud Test 2, DuPont |
| 6 | `total_assets` | 总资产 | Balance Sheet | Fraud Test 3, DuPont |
| 7 | `short_term_borrowing` | 短期借款 | Balance Sheet | Fraud Test 3 |
| 8 | `long_term_borrowing` | 长期借款 | Balance Sheet | Fraud Test 3 |
| 9 | `bonds_payable` | 应付债券 | Balance Sheet | Fraud Test 3 |
| 10 | `net_profit` | 净利润 | Income Statement | DuPont, OCF Ratio |
| 11 | `total_equity` | 股东权益 | Balance Sheet | DuPont |
| 12 | `operating_cash_flow` | 经营活动现金流净额 | Cash Flow Statement | OCF Ratio |
| 13 | `cost_of_revenue` | 营业成本 | Income Statement | DuPont (gross margin) |
| 14 | `total_liabilities` | 总负债 | Balance Sheet | DuPont (leverage) |
| 15 | `inventory` | 存货 | Balance Sheet | Health (turnover) |
| 16 | `total_current_assets` | 流动资产 | Balance Sheet | Health |
| 17 | `total_current_liabilities` | 流动负债 | Balance Sheet | Health |
| 18 | `depreciation_amortization` | 折旧摊销 | Cash Flow Statement | Health |
| 19 | `capex` | 资本开支 | Cash Flow Statement | Health (free cash flow) |
| 20 | `report_period` | 报告期 | All | Time series key |

### 3.3 Storage

```
Engine:  SQLite
File:    data/financial.db
Table:   financial_data

Schema:
    stock_code    TEXT NOT NULL,     -- e.g. '600519'
    report_date   TEXT NOT NULL,     -- e.g. '2025-09-30' (YYYY-MM-DD)
    data_payload  TEXT NOT NULL,     -- JSON string of 20 fields
    updated_at    TEXT NOT NULL,     -- ISO 8601 timestamp
    PRIMARY KEY (stock_code, report_date)

Index:
    CREATE INDEX idx_stock ON financial_data(stock_code);
```

**Size estimate**: 5,000 stocks × 20 reports (5 years quarterly) × ~500 bytes/row ≈ 50 MB

### 3.4 Data Fetching Strategy

```
1. Check SQLite for existing data
2. If missing or stale (> 24h for latest quarter):
   a. Fetch from AKShare (ak.stock_financial_report_sina)
   b. Extract 20 key fields from raw response
   c. Upsert into SQLite
3. Return data as pandas DataFrame
```

---

## 4. Fraud Detection Algorithms (Step 1)

### 4.1 Test 1: Interest Income Anomaly (利息收支异常)

**Logic**: If a company claims large cash reserves but earns negligible interest, the cash may be fabricated or misappropriated.

```python
implied_yield = interest_income / monetary_funds
flag = implied_yield < 0.005  # threshold: 0.5%
```

**Inputs**: `monetary_funds`, `interest_income`
**Output**: `{ passed: bool, ratio: float, threshold: 0.005 }`
**Edge cases**:
- `monetary_funds == 0` → skip test (mark as N/A, not fail)
- `interest_income < 0` → flag immediately (negative interest income is abnormal)

### 4.2 Test 2: Revenue-Receivable Divergence (收现背离)

**Logic**: If accounts receivable grows much faster than revenue, the company may be booking fake sales.

```python
ar_growth = (ar_current - ar_previous) / ar_previous
rev_growth = (rev_current - rev_previous) / rev_previous
divergence_ratio = ar_growth / rev_growth
flag = divergence_ratio > 2.0  # AR growing 2x faster than revenue
```

**Inputs**: `accounts_receivable` (current + previous period), `revenue` (current + previous period)
**Output**: `{ passed: bool, ar_growth: float, rev_growth: float, divergence: float, threshold: 2.0 }`
**Edge cases**:
- `rev_growth <= 0` and `ar_growth > 0` → flag (revenue shrinking but AR growing)
- `rev_growth == 0` → avoid division by zero, flag if `ar_growth > 0.1`
- Both negative → skip (both shrinking is not this specific pattern)

### 4.3 Test 3: High Cash + High Debt (存贷双高)

**Logic**: A company with both large cash and large debt simultaneously is suspicious — why borrow at high interest when sitting on cash?

```python
interest_bearing_debt = short_term_borrowing + long_term_borrowing + bonds_payable
ratio = (monetary_funds + interest_bearing_debt) / total_assets
flag = ratio > 0.6 and interest_expense / interest_bearing_debt > 0.04
```

**Inputs**: `monetary_funds`, `short_term_borrowing`, `long_term_borrowing`, `bonds_payable`, `total_assets`, `interest_expense`
**Output**: `{ passed: bool, cash_debt_ratio: float, debt_cost: float, thresholds: { ratio: 0.6, cost: 0.04 } }`
**Edge cases**:
- `interest_bearing_debt == 0` → pass (no debt = no anomaly)
- `total_assets == 0` → error state, skip analysis

### 4.4 Circuit Breaker Decision

```python
breaker_result = {
    "tripped": any(not t.passed for t in [test1, test2, test3]),
    "tests": [test1, test2, test3],
    "failed_tests": [t for t in tests if not t.passed],
}
```

If `tripped == True` → return result immediately, do NOT run Step 2.

---

## 5. Health Profile Algorithms (Step 2)

Only executed when all 3 fraud tests pass.

### 5.1 DuPont Analysis (ROE Decomposition)

```python
net_margin = net_profit / revenue                    # 净利率
asset_turnover = revenue / total_assets              # 资产周转率
equity_multiplier = total_assets / total_equity      # 权益乘数
roe = net_margin * asset_turnover * equity_multiplier # ROE
```

**Output**: `{ roe: float, net_margin: float, asset_turnover: float, equity_multiplier: float }`

### 5.2 Cash Flow Quality

```python
ocf_ratio = operating_cash_flow / net_profit
```

**Interpretation**:
- `> 1.0` → Cash generation exceeds reported profit (healthy)
- `0.5 - 1.0` → Moderate, worth monitoring
- `< 0.5` → Profit not backed by cash (warning)

**Output**: `{ ocf_ratio: float, quality: "healthy" | "moderate" | "warning" }`

---

## 6. UI Design (workUI.html)

### 6.1 Layout Structure

```
Header (unchanged)
Search Bar (unchanged)
KPI Cards (unchanged — always shows VPU metrics)
┌─────────────────────────────────────────────────────────────┐
│ Analysis Card                      [VPU 分析] [财务分析]     │ ← tab pills, right-aligned
│ ┌─────────────────────────────────────────────────────────┐ │
│ │  Tab Content Area                                       │ │
│ │  - VPU tab: existing chart (K-line + VPU bars)          │ │
│ │  - Financial tab: fraud scan + health profile           │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
Parameters Bar (unchanged)
Footer (unchanged)
```

### 6.2 Tab Switching

- Two pill buttons right-aligned in the Analysis Card toolbar
- Active: `bg-primary text-white rounded-full`
- Inactive: `text-slate-500 hover:bg-slate-100 dark:hover:bg-primary/10 rounded-full`
- JS toggles `hidden` class on two content divs

### 6.3 Financial Tab — Fraud Scan Section

Three audit test cards, horizontal layout (3 columns on desktop, stacked on mobile):

```html
<!-- Each test card -->
<div class="border-l-4 border-{green|red}-500 bg-{green|red}-950/20 rounded-r-lg p-4">
  <div class="flex justify-between items-center">
    <span class="font-bold">{Test Name}</span>
    <span class="pill badge">{PASS|FAIL}</span>
  </div>
  <div class="text-sm text-slate-400 mt-2">
    {metric}: {value} vs threshold: {threshold}
  </div>
  <div class="text-xs text-slate-500 mt-1">{one-line explanation}</div>
</div>
```

### 6.4 Financial Tab — Gate Banner

Below the 3 test cards:

**Pass state** (all green):
```html
<div class="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-4 flex items-center gap-3">
  <span class="text-emerald-400">✅</span>
  <span>财务诚信验证通过 — 健康度分析已解锁</span>
</div>
```

**Fail state** (any red):
```html
<div class="bg-red-950/50 border border-red-500/30 rounded-xl p-4 flex items-center gap-3">
  <span class="text-red-400">⛔</span>
  <span>财务风险预警 — {failed_test_name} 异常，健康度分析已终止</span>
</div>
```

### 6.5 Financial Tab — Health Section (Pass Only)

Two sub-sections with mock charts (CSS-only):

**DuPont Analysis**: ROE decomposition displayed as 4 metric cards + formula visualization
**Cash Flow Quality**: OCF/净利润 ratio with colored status badge

### 6.6 Demo Toggle

Hidden button (bottom-right, small text) to switch between pass/fail mock states for browser preview.

### 6.7 Mock Data

**Pass state (贵州茅台 600519)**:
```json
{
  "monetary_funds": 180000000000,
  "interest_income": 3800000000,
  "implied_yield": 0.0211,
  "accounts_receivable": 2800000000,
  "revenue": 145000000000,
  "ar_growth": 0.05,
  "rev_growth": 0.15,
  "short_term_borrowing": 0,
  "long_term_borrowing": 0,
  "bonds_payable": 0,
  "total_assets": 280000000000,
  "net_profit": 74000000000,
  "total_equity": 210000000000,
  "operating_cash_flow": 85000000000,
  "roe": 0.352,
  "ocf_ratio": 1.15
}
```

**Fail state (fabricated)**:
```json
{
  "monetary_funds": 80000000000,
  "interest_income": 230000000,
  "implied_yield": 0.0029,
  "accounts_receivable": 15000000000,
  "revenue": 30000000000,
  "ar_growth": 0.45,
  "rev_growth": 0.14,
  "divergence_ratio": 3.21,
  "short_term_borrowing": 20000000000,
  "long_term_borrowing": 30000000000,
  "bonds_payable": 10000000000,
  "total_assets": 120000000000,
  "interest_expense": 3500000000,
  "cash_debt_ratio": 1.17
}
```

---

## 7. Module Architecture

```
stock-vpu/
├── financial_analyzer.py      # Circuit breaker engine (Step 1 + Step 2)
├── financial_fetcher.py       # AKShare data fetching + SQLite storage
├── data/
│   └── financial.db           # SQLite database (auto-created)
├── workUI.html                # Updated: dual-tab UI with financial analysis
├── test_financial.py          # Unit + integration tests
└── spec-financial.yaml        # System specification
```

### Module Dependencies

```
financial_fetcher.py
    ↓ (provides DataFrame)
financial_analyzer.py
    ├── fraud_scan()          → Step 1
    └── health_profile()      → Step 2 (only if Step 1 passes)
    ↓ (results dict)
workUI.html (mock data)
app.py / api_server.py (future integration)
```

---

## 8. Color Grammar

| State | Background | Border | Text | Use |
|-------|-----------|--------|------|-----|
| Pass | `bg-emerald-950/20` | `border-emerald-500` | `text-emerald-400` | Test passed |
| Fail | `bg-red-950/20` | `border-red-500` | `text-red-400` | Test failed |
| Locked | `bg-slate-900/50` | `border-slate-700` | `text-slate-500` | Health section when breaker tripped |
| Neutral | `bg-card-dark` | `border-primary/10` | `text-slate-100` | Default card |
| Healthy | `bg-emerald-950/10` | — | `text-emerald-400` | OCF ratio > 1.0 |
| Warning | `bg-amber-950/10` | — | `text-amber-400` | OCF ratio 0.5-1.0 |
| Danger | `bg-red-950/10` | — | `text-red-400` | OCF ratio < 0.5 |
