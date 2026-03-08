# Stock-VPU Improvement TODO List

## Phase 1: Code Optimization & Robustness (High Priority)
- [x] **Task 1.1: Enhanced Data Validation Layer**
    - [x] Create `data_validator.py`
    - [x] Implement `validate_stock_code`, `validate_date_range`, `validate_dataframe`
    - [x] Migrate logic from `config.py`
- [x] **Task 1.4: Enhanced Logger System**
    - [x] Create `logger.py`
    - [x] Implement rotating file handler and console logging
    - [x] Integrate into `main.py` and `data_fetcher.py`
- [x] **Task 1.3: Enhanced Caching**
    - [x] Create `cache_manager.py`
    - [x] Implement file-based pickle cache with TTL
    - [x] Integrate into `data_fetcher.py`
- [x] **Task 1.2: Performance Optimization**
    - [x] Refactor `calculator.py` for full vectorization (especially `aggregate_daily`)
    - [x] Verify performance gains

## Phase 2: Feature Enhancement & UX (Medium Priority)
- [x] **Task 2.1: Batch Processing**
    - [x] Create `batch_processor.py`
    - [x] Support list of stocks and comparison reports
- [x] **Task 2.2: Advanced Visualization**
    - [x] Enhance `visualizer.py` with comparison charts and heatmaps (implemented in `advanced_visualizer.py`)
- [x] **Task 2.3: Technical Analysis Indicators**
    - [x] Create `technical_analyzer.py` (RSI, Bollinger, MACD)
- [x] **Task 2.4: Data Export Enhancements**
    - [x] Create `export_manager.py` (Excel, JSON, Parquet, HTML)

## Phase 3: Architecture & Scalability (Low Priority)
- [x] **Task 3.1: Plugin Architecture**
- [x] **Task 3.2: REST API (FastAPI)**
- [x] **Task 3.3: Dockerization**
- [x] **Task 3.4: CI/CD Pipeline Enhancement**
