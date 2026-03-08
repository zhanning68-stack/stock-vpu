# 📊 Stock VPU - 股票流动性深度指标分析工具

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

> **VPU (Volume Per Price Unit)** - 单位价差成交量：推动股价变动一个最小计价单位所需的平均成交量。值越大，市场越"厚"，流动性越好；值越小，价格越容易被推动。

---

## ✨ 功能特性

- 📈 **多维度指标**：VPU（成交量版）+ APU（成交额版）+ 方向性分析（VPU_Up/Down）
- 📊 **交互式 K 线联动**：主图 K 线行为与副图流动性压力实时联动，支持专业暗色主题
- 🚀 **企业级架构**：模块化设计，解耦计算、存储、验证与展示逻辑
- 🌐 **RESTful API**：基于 FastAPI 提供高性能异步接口，支持下游系统集成
- 🔄 **批量处理**：内置批量处理器，支持多股对比分析与相关性研究
- 📂 **全格式导出**：支持 CSV, Excel, JSON, Parquet, HTML 等格式
- ⚡ **智能缓存**：支持内存与文件双级缓存，TTL 可配，减少 API 调用压力
- 🐳 **容器化**：提供 Docker 支持，一键部署生产级分析环境
- ✅ **健壮性**：内置数据验证器，覆盖 A 股全市场，集成 GitHub Actions CI

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 方式一：Streamlit 网页仪表盘（推荐）

```bash
# 启动 Web UI
streamlit run app.py
```

打开浏览器访问 `http://localhost:8501`，即可使用增强型交互界面：

- **核心看板**：实时计算 VPU/APU 指标，展示平均抛压（VPU_Up）与支撑（VPU_Down）。
- **技术分析**：支持叠加 RSI、布林带等技术指标进行综合研判。
- **多股对比**：支持输入多个股票代码，生成趋势对比图及相关性热力图。
- **参数调优**：实时调节截尾比例、最小价差等核心算法参数。
- **一键导出**：支持 CSV 数据直接下载。

### 方式二：命令行 CLI

```bash
# 查看帮助
python main.py --help

# 基础查询
python main.py 600519
```

### 方式三：FastAPI 接口服务

```bash
# 启动 API 服务
python api_server.py
```

访问 `http://localhost:8000/docs` 查看 Swagger 文档。支持 POST 请求计算 VPU：

```bash
curl -X POST "http://localhost:8000/api/v1/calculate" \
     -H "Content-Type: application/json" \
     -d '{"code": "600519", "start_date": "2024-01-01", "end_date": "2024-03-01"}'
```

### 方式四：Docker 部署

```bash
# 使用 Docker Compose 一键启动 (Web + API)
docker-compose up -d
```

---

## 📐 核心指标说明

### VPU (Volume Per Price Unit)

```
VPU = 成交量（手） / max(1, ceil(前复权价差 / 0.05))
```

- **使用场景**：单只股票的历史纵向比较
- **复权策略**：前复权价格，保证跨除权日的量价连续性

### APU (Amount Per Price Unit)

```
APU = 成交额（元） / max(1, ceil(未复权价差 / 0.05))
```

- **使用场景**：跨股票的横向比较
- **复权策略**：未复权价格，保证成交额与价格尺度绝对一致

### 方向性指标

| 指标 | 含义 | 解读 |
|------|------|------|
| VPU_Up | 上涨单元平均 VPU | 值越大，上方抛压越重，上涨越困难 |
| VPU_Down | 下跌单元平均 VPU | 值越大，下方支撑越强，下跌越困难 |

**多空力量对比**：
- VPU_Up >> VPU_Down → 上涨需要更多成交量推动，上方抛压重
- VPU_Up << VPU_Down → 下跌需要更多成交量推动，下方支撑强
- VPU_Up ≈ VPU_Down → 多空力量均衡

---

## ⚙️ 可配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `PRICE_UNIT` | 0.05 | 最小价差单位（元） |
| `TRIM_RATIO` | 0.25 | 截尾比例（上下各截掉25%，保留中间50%） |
| `MIN_VALID_UNITS` | 10 | 每日最少有效单元数，不足则该日作废 |
| `MIN_PRICE_SPREAD` | 0.03 | 最小有效价差（元），低于此值的单元剔除 |
| `MA_PERIODS` | [5, 10] | 移动平均周期 |
| `SKIP_FIRST_LAST` | True | 是否剔除首尾5分钟单元（开盘/收盘竞价） |
| `ENABLE_DIRECTION` | True | 是否计算方向性指标（VPU_Up / VPU_Down） |

---

## 🗂️ 项目结构

```
stock-vpu/
├── app.py               # Streamlit 网页端
├── main.py              # CLI 命令行工具
├── api_server.py        # FastAPI 服务
├── calculator.py        # 核心计算引擎
├── data_fetcher.py      # 数据采集模块
├── visualizer.py        # 基础可视化
├── advanced_visualizer.py # 高级对比可视化
├── data_validator.py    # 数据验证中心
├── cache_manager.py     # 持久化缓存
├── export_manager.py    # 导出中心
├── logger.py            # 统一日志
├── batch_processor.py   # 批量分析引擎
├── plugin_system.py     # 插件扩展
├── technical_analyzer.py # 技术分析指标
├── config.py            # 全局配置
├── Dockerfile           # 镜像构建
└── docker-compose.yml   # 容器编排
```

---

## 🔧 技术栈

| 组件 | 选型 | 用途 |
|------|------|------|
| 数据源 | [AKShare](https://www.akshare.xyz/) | 免费开源，东财/新浪数据源，5分钟K线 |
| 数据处理 | pandas | 数据清洗、分组聚合、时间序列处理 |
| 可视化 | Streamlit + ECharts | 交互式网页图表（深色量化终端主题） |
| 静态导出 | matplotlib | CLI 环境下生成 PNG 报告 |
| 缓存 | @st.cache_data | 减少 API 调用，TTL=3600s |
| CI | GitHub Actions | pytest 矩阵测试（Python 3.10/3.11/3.12） |

---

## 📊 数据清洗规则

计算前自动执行以下清洗（按优先级）：

| 规则 | 条件 | 原因 |
|------|------|------|
| R1. 涨跌停日 | 当日最高价或最低价触及涨跌停价 | 成交行为异常，流动性指标无意义 |
| R2. 首尾单元 | 9:30-9:35 和 14:55-15:00 | 集合竞价/尾盘抢单导致数据失真 |
| R3. 零价差单元 | 最高价 == 最低价 | 除零风险，且横盘无价格发现意义 |
| R4. 极低振幅单元 | 价差 < MIN_PRICE_SPREAD | 波动过小导致 VPU 异常膨胀 |

> 若某日有效单元数 < 10，该日标记为"数据不足"，不参与指标计算。

---

## 📝 使用示例

### 示例 1：分析贵州茅台（600519）流动性

```bash
python main.py 600519 -s 2024-01-01 -e 2024-03-01 -o all
```

输出：
```
Stock Code: 600519
Date Range: 2024-01-01 to 2024-03-01
Trading Days: 42

      date       vpu    vpu_up  vpu_down  close_price
2024-01-02  15234.56  18234.12  12456.78      1680.50
2024-01-03  14890.23  17567.89  12345.67      1675.30
...

PNG exported to: ./output/600519_vpu_20240301.png
CSV exported to: ./output/600519_vpu_20240301.csv
```

### 示例 2：对比创业板股票（300750）

```bash
python main.py 300750 --trim-ratio 0.20
```

> 创业板涨跌停阈值为 20%，程序会自动识别并应用正确的阈值。

---

## 🔍 涨跌停阈值规则

| 股票类型 | 代码前缀 | 涨跌停阈值 |
|----------|----------|------------|
| 主板 | 600/601/603/000/001/002 | ±9.8% |
| 科创板 | 688 | ±19.8% |
| 创业板 | 300/301 | ±19.8% |
| ST 股 | - | ±4.8% |

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- 数据源：[AKShare](https://www.akshare.xyz/) - 开源财经数据接口库
- 可视化：[Apache ECharts](https://echarts.apache.org/) - 开源可视化库
- UI 框架：[Streamlit](https://streamlit.io/) - 快速构建数据应用

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [GitHub Issue](../../issues)
- 发送邮件至 [your-email@example.com](mailto:your-email@example.com)

---

<p align="center">
  <sub>Made with ❤️ for quantitative trading analysis</sub>
</p>
