# 方案 B 设计文档：K线融合深度视图 (Candlestick Integration)

## 1. 目标
将流动性指标 (VPU) 与价格行为 (OHLC) 深度整合，通过上下分屏联动的方式，直观展示流动性深度如何驱动价格变化。

## 2. 视觉规格
- **布局**：上下双 Grid 结构。
  - Grid 0 (Top, 60%): K线图 (Candlestick) + MA5/MA10。
  - Grid 1 (Bottom, 30%): VPU 零轴对立柱状图。
- **配色**：
  - 阳线: `#ef5350` (柔和红)
  - 阴线: `#26a69a` (柔和绿)
  - VPU Up: 红色渐变 `rgba(239, 83, 80, 0.8)` -> `rgba(239, 83, 80, 0.1)`
  - VPU Down: 绿色渐变 `rgba(38, 166, 154, 0.8)` -> `rgba(38, 166, 154, 0.1)`
- **联动**：通过 `axisPointer.link` 实现上下 X 轴完全同步。

## 3. 数据流改动
- **calculator.py**: `calculate_vpu` 需要在最终返回的 DataFrame 中保留 `open`, `high`, `low`, `close` 等原始 K 线字段。
- **visualizer.py**: 
  - `render_chart` 函数签名不变，但内容重构为双 Grid 模式。
  - 处理 ECharts 的 `dataset` 或多 `series` 映射。

## 4. 交互增强
- **Tooltip**: 统一显示该日期的 OHLC 及 VPU 数值。
- **DataZoom**: 放在最下方，同时控制两个图表的缩放。

## 5. 验收标准
- [ ] 页面显示上下两个联动的图表。
- [ ] 上方为蜡烛图，下方为对立柱状图。
- [ ] 缩放其中一个图表时，另一个自动同步。
- [ ] Tooltip 包含所有维度数据。
