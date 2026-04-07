# TradeHive — 功能改动记录

> **基线（Baseline）**：原始 [TradingAgents](https://github.com/Handshakeworm/TradeHive) 仓库，仅支持通过 yfinance / Alpha Vantage 获取美股数据，不支持加密货币、宏观指标或情绪分析。
>
> 本文件记录从基线出发的所有功能模块新增与调整，以证明项目是在原始代码基础上进行结构性修改，而非简单复制。

---

## 版本：v0.3.0 — 数据源扩展 + 新 Analyst Agent 接入

**改动日期**：2026-03-28  
**改动摘要**：新增加密货币、宏观经济、情绪分析三类数据源及对应 Analyst Agent；修复数据配置覆盖 Bug；新增 Parquet 本地缓存层

---

## 一、新增功能模块

### 1.1 加密货币数据支持

**基线缺失**：原始版本只支持美股数据，无任何加密货币接口。

**新增内容**：
- 接入 CoinGecko API，支持实时加密货币价格快照与市场总览
- 历史 OHLCV 数据通过 yfinance（`BTC-USD` 格式）获取，保证完整历史覆盖
- 新增 **Crypto Analyst Agent**，可自主调用加密货币数据工具，生成市场分析报告

### 1.2 宏观经济数据支持

**基线缺失**：原始版本无任何宏观经济数据接入。

**新增内容**：
- 接入 FRED（美联储经济数据库）API，覆盖联邦基金利率、CPI、失业率、VIX、10年期国债收益率等 16 个核心宏观系列
- 支持单指标历史序列查询和多指标快照两种模式
- 新增 **Macro Analyst Agent**，负责从宏观角度分析市场环境，辅助交易决策

### 1.3 情绪分析支持

**基线缺失**：原始版本无结构化情绪评分机制。

**新增内容**：
- 集成 VADER 情绪分析模型，对 yfinance 抓取的新闻标题和摘要进行离线情绪评分（-1 至 +1）
- 可选接入 Reddit PRAW，获取社交媒体情绪；若未配置则自动降级为新闻情绪
- 新增 **Sentiment Analyst Agent**，输出结构化情绪报告供交易图使用

### 1.4 本地数据缓存层

**基线缺失**：原始版本每次运行均重新调用 API，无任何数据持久化机制。

**新增内容**：
- 新增基于 Parquet 格式的文件缓存模块，数据首次获取后写入本地，后续直接读取缓存
- 统一缓存路径结构：`data_cache/{category}/{symbol}/{start}_{end}.parquet`
- 缓存数据可直接供 RAP 向量库（Task 3）复用，无需重复采集

---

## 二、调整的原有功能模块

### 2.1 数据路由层扩展

**调整前**：数据路由仅支持 `yfinance` 和 `alpha_vantage` 两个数据源，只有股票相关类别。

**调整后**：新增 `coingecko`、`fred`、`vader` 三个数据源及对应路由类别（`crypto_data` / `macro_data` / `sentiment_data`），新工具函数通过统一路由机制调用，与原有机制完全兼容。

### 2.2 默认配置扩展

**调整前**：`data_vendors` 配置只涵盖股票相关数据源，无缓存配置项。

**调整后**：配置新增加密货币、宏观、情绪三类数据源的默认 vendor 指定，以及本地缓存开关和缓存目录配置（支持通过环境变量覆盖）。

### 2.3 Agent 图扩展

**调整前**：LangGraph 交易图只支持注册 market / social / news / fundamentals 四种 Analyst 节点。

**调整后**：图注册逻辑新增对 sentiment / crypto / macro 三类 Analyst 的支持，与原有四种 Analyst 完全对称，通过 `selected_analysts` 参数按需启用，不影响原有默认流程。

### 2.4 入口配置修复

**调整前**：`main.py` 中对 `data_vendors` 的赋值会覆盖配置中新增的数据源字段，导致新功能失效（Bug）。

**调整后**：修复覆盖问题，确保所有数据源配置完整保留；新增加密货币分析和全量 Analyst 的示例用法（注释形式，不影响默认运行）。

### 2.5 依赖与环境配置

**调整前**：项目依赖中不包含新数据源所需包；`.env.example` 只有 LLM 的 API Key 占位符。

**调整后**：
- 新增四个依赖包：`fredapi`（宏观数据）、`vaderSentiment`（情绪分析）、`pyarrow`（Parquet 缓存）、`praw`（Reddit，可选）
- `.env.example` 补充 FRED、Reddit 等数据源的 API Key 说明及申请链接，方便团队成员配置

---

## 三、设计决策说明

### 为什么新增 Analyst Agent 而不修改原有 Agent？

原有四个 Analyst 已有稳定的调用接口和节点注册逻辑。新增独立 Agent 可按需启用，不破坏已有流程，符合开闭原则。

### 为什么加密货币历史数据用 yfinance 而非仅 CoinGecko？

CoinGecko 免费接口获取完整历史数据有限制，yfinance 的 `BTC-USD` 格式支持任意时间段历史数据，稳定性更好。CoinGecko 保留用于实时快照场景。

### 为什么用 Parquet 文件缓存而非数据库？

项目以研究为主，Parquet 格式轻量、零服务依赖，pandas 原生读写，且可直接供 RAP 向量库使用，无需额外接口转换。

---

## 四、安装与运行

```bash
# 1. 安装依赖（含新增包）
pip install -e .
pip install fredapi vaderSentiment pyarrow praw yfinance

# 2. 配置 API Keys
cp .env.example .env
# 填写 OPENAI_API_KEY（或 OPENROUTER_API_KEY）
# 可选：FRED_API_KEY（使用宏观分析师时需要）

# 3. 运行 demo（NVDA 2024-05-10）
python main.py
```

---

---

## 版本：v0.3.1 — Tools 暴露机制修复

**改动日期**：2026-04-03  
**改动摘要**：审查多 Agent 系统 tools 暴露规则，修复 LLM bind_tools 与 Graph ToolNode 不对齐问题，补全 News Analyst 工具能力

---

### 修复内容

#### 1. News Analyst 工具层不对齐（已修复）

**问题**：`get_insider_transactions` 在 Graph ToolNode（`trading_graph.py`）中已注册到 `tools_news` 节点，但 News Analyst（`news_analyst.py`）的 `llm.bind_tools()` 未包含该工具。LLM 不知道此工具存在，导致内幕交易数据在整个系统中从未被任何 Agent 实际调用。

**修复**：
- `news_analyst.py`：import 中新增 `get_insider_transactions`，tools 列表从 2 个补全为 3 个
- 修复后 LLM bind_tools 与 ToolNode 完全对齐：`get_news`、`get_global_news`、`get_insider_transactions`

**涉及文件**：`tradingagents/agents/analysts/news_analyst.py`


---

## 版本：v0.4.0 — 移除 Sentiment Analyst 节点

**改动日期**：2026-04-04  
**改动摘要**：移除 Sentiment Analyst Agent 节点及其全部图注册、工具绑定、条件路由逻辑，精简分析师管线

---

### 移除内容

#### Sentiment Analyst 节点完整移除

**移除原因**：精简 Agent 管线，去除冗余分析节点。

**涉及文件与改动**：

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/analysts/sentiment_analyst.py` | **删除**（整个文件） |
| `tradingagents/agents/__init__.py` | 移除 `create_sentiment_analyst` 的 import 及 `__all__` 导出 |
| `tradingagents/graph/conditional_logic.py` | 移除 `should_continue_sentiment()` 条件路由方法 |
| `tradingagents/graph/setup.py` | 移除 `if "sentiment" in selected_analysts` 节点创建块 |
| `tradingagents/graph/trading_graph.py` | 移除 `"sentiment"` ToolNode 及 `get_news_sentiment`/`get_reddit_sentiment` import |
| `main.py` | 移除注释示例中的 `"sentiment"` 选项 |

**未受影响**：
- `sentiment_report` 字段保留于 `AgentState`，由 `propagation.py` 初始化为空字符串，下游节点正常兼容
- `sentiment_utils.py` 数据工具模块保留，可供其他模块复用
- `cli/main.py` 中 `sentiment_report` 的显示逻辑绑定于 Social Analyst，不受影响
- 图的前后节点由 `setup.py` 循环自动连接，移除后无需手动补边







---

## 版本：v0.4.1 — Social Media Analyst 改名为 Sentiment Analyst

**改动日期**：2026-04-04  
**改动摘要**：将 Social Media Analyst 节点统一改名为 Sentiment Analyst，同步更新图注册 key、条件路由、状态字段、CLI 映射等全部引用；功能与 prompt 保持不变

---

### 改名映射

| 项目 | 旧值 | 新值 |
|------|------|------|
| 文件名 | `social_media_analyst.py` | `sentiment_analyst.py` |
| 工厂函数 | `create_social_media_analyst()` | `create_sentiment_analyst()` |
| 图 key / `selected_analysts` | `"social"` | `"sentiment"` |
| 条件路由方法 | `should_continue_social()` | `should_continue_sentiment()` |
| 图节点名 | `Social Analyst` / `Msg Clear Social` / `tools_social` | `Sentiment Analyst` / `Msg Clear Sentiment` / `tools_sentiment` |
| 输出状态字段 | `community_report` | `sentiment_report` |
| CLI 枚举 | `AnalystType.SOCIAL` | `AnalystType.SENTIMENT` |

### 涉及文件

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/analysts/sentiment_analyst.py` | 由 `social_media_analyst.py` 重命名；函数名 + 输出字段更新 |
| `tradingagents/agents/__init__.py` | import 路径及 `__all__` 导出更新 |
| `tradingagents/graph/conditional_logic.py` | `should_continue_social` → `should_continue_sentiment` |
| `tradingagents/graph/setup.py` | 所有 `"social"` → `"sentiment"`；默认列表及文档注释同步 |
| `tradingagents/graph/trading_graph.py` | 默认 `selected_analysts` 及 ToolNode key 更新 |
| `tradingagents/agents/utils/agent_states.py` | 移除 `community_report` 字段（不再需要） |
| `tradingagents/agents/researchers/bull_researcher.py` | 移除 `community_report` 读取与拼接 |
| `tradingagents/agents/researchers/bear_researcher.py` | 同上 |
| `tradingagents/agents/trader/trader.py` | 同上 |
| `tradingagents/agents/risk_mgmt/aggressive_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/neutral_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/conservative_debator.py` | 同上 |
| `main.py` | `selected_analysts` 列表中 `"social"` → `"sentiment"` |
| `cli/models.py` | `SOCIAL` → `SENTIMENT` |
| `cli/main.py` | 所有 `"social"` key 及 `"Social Analyst"` 显示名更新 |

### 说明

- **功能不变**：Agent 的 system prompt、工具绑定（`get_news`）、分析逻辑完全不变，仅改名
- **输出字段合并**：原 `community_report`（仅 social media analyst 写入）合并到已有的 `sentiment_report`，下游 8 个节点原本就直接读取 `sentiment_report`，无需改动
- **`propagation.py` 无需修改**：`sentiment_report` 已在初始状态中初始化为空字符串


---

## 版本：v0.4.2 — 删除 `get_crypto_price` 工具

**改动日期**：2026-04-04  
**改动摘要**：删除 `get_crypto_price` 工具，该工具调用 CoinGecko API 只返回实时快照，不接受日期参数，无法支持回测场景。使用 `get_crypto_historical` 替代，它通过 yfinance 支持任意历史日期范围。

---

### 涉及文件

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/coingecko.py` | 删除 `get_crypto_price()` 函数定义 |
| `tradingagents/agents/utils/crypto_tools.py` | 删除 `get_crypto_price` tool wrapper |
| `tradingagents/agents/analysts/crypto_analyst.py` | 移除 import、tools 列表引用、prompt 中的工具说明、docstring |
| `tradingagents/agents/utils/agent_utils.py` | 移除 import |
| `tradingagents/dataflows/interface.py` | 移除 import、`TOOLS_CATEGORIES` 条目、`VENDOR_METHODS` 条目 |
| `tradingagents/graph/trading_graph.py` | 移除 import 及 ToolNode 中的引用 |

---

## 版本：v0.5.0 — 清理不支持回测的 yfinance 数据源，合并 `get_news_sentiment`

**改动日期**：2026-04-04  
**改动摘要**：项目只做回测，删除无法提供历史数据的 yfinance vendor（`get_news`、`get_global_news`、`get_fundamentals`），统一使用 Alpha Vantage；删除 `get_news_sentiment` 工具，因 Alpha Vantage NEWS_SENTIMENT API 已自带情绪评分

---

### 一、删除 yfinance news vendor

**删除原因**：yfinance `get_news` 只返回最新 20 条、`get_global_news` 的 `yf.Search()` 只搜当前新闻，均无法用于历史回测。Alpha Vantage NEWS_SENTIMENT 端点支持 `time_from/time_to` 任意历史区间查询。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/yfinance_news.py` | **删除**（整个文件，包含 `get_news_yfinance` 和 `get_global_news_yfinance`） |
| `tradingagents/dataflows/interface.py` | 移除 `from .yfinance_news import ...`；移除 `VENDOR_METHODS["get_news"]` 和 `["get_global_news"]` 中的 yfinance 条目 |

### 二、删除 yfinance fundamentals vendor

**删除原因**：`ticker.info` 只返回当前快照，无历史接口。Alpha Vantage OVERVIEW 端点同样为当前快照，但统一数据源减少依赖。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 移除 `get_fundamentals as get_yfinance_fundamentals` import；移除 `VENDOR_METHODS["get_fundamentals"]` 中的 yfinance 条目 |

### 三、`get_insider_transactions` 只保留 yfinance vendor

**原因**：两边数据源头都是 SEC 公开披露（Form 4），质量无差异；yfinance 免费无配额限制，Alpha Vantage 消耗 API 配额。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 移除 `get_alpha_vantage_insider_transactions` import 及 `VENDOR_METHODS` 中的 alpha_vantage 条目 |

### 四、删除 `get_news_sentiment` 工具

**删除原因**：该工具从 yfinance 拉新闻后用 VADER 做情绪评分，与 `get_news` 数据源重复。Alpha Vantage NEWS_SENTIMENT API 已自带 `overall_sentiment_score`、`ticker_sentiment_score` 等字段，无需单独情绪评分步骤。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/sentiment_utils.py` | 删除 `get_news_sentiment()` 函数和 `_save_sentiment_cache()` 内部函数 |
| `tradingagents/dataflows/interface.py` | 移除 `get_news_sentiment` 的 import、`TOOLS_CATEGORIES` 条目、`VENDOR_METHODS` 条目 |
| `tradingagents/agents/utils/sentiment_tools.py` | 删除 `get_news_sentiment` @tool 包装函数 |
| `tradingagents/agents/utils/agent_utils.py` | 移除 `get_news_sentiment` import |

### 五、`get_news` 新增 `limit` 和 `sort` 参数

**原因**：Alpha Vantage NEWS_SENTIMENT API 默认可返回 200+ 条新闻，全部灌给 LLM 浪费 token。新增 `limit=30`（默认）和 `sort=RELEVANCE`（按 ticker 相关性排序），控制输入量同时保证最相关的新闻优先返回。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_news.py` | `get_news()` 新增 `limit` 参数（默认 30），API 请求加 `limit` 和 `sort=RELEVANCE` |

### 六、变更后 vendor 映射

| 工具 | 可用 vendor |
|------|------------|
| `get_news` | `alpha_vantage` |
| `get_global_news` | `alpha_vantage` |
| `get_fundamentals` | `alpha_vantage` |
| `get_insider_transactions` | `yfinance` |

### 七、未受影响

- `sentiment_utils.py` 中 VADER 核心函数（`score_text_sentiment`、`_label_sentiment`、`_get_vader`）和 `get_reddit_sentiment` 保留
- `sentiment_tools.py` 中 `get_reddit_sentiment` @tool 保留
- `y_finance.py` 中 `get_fundamentals` 函数本体保留（仅不再注册为 vendor）

---

## 版本：v0.5.1 — 数据层日期截断防泄漏 + 财报 vendor 精简

**改动日期**：2026-04-04  
**改动摘要**：回测场景下数据工具可能返回"未来"数据，造成数据泄漏。在数据层加日期截断逻辑；财报删除 yfinance vendor 只保留 Alpha Vantage（有 `reportedDate` 可严格按披露日过滤）

---

### 一、删除 yfinance 财报 vendor

**删除原因**：yfinance 财报只有 `fiscalDateEnding`（会计期结束日），无法区分报表是否已实际披露。Alpha Vantage 有 `reportedDate`（实际披露日），可严格按披露日过滤防止数据泄漏。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 移除 `get_yfinance_balance_sheet`、`get_yfinance_cashflow`、`get_yfinance_income_statement` 的 import 及 `VENDOR_METHODS` 中的 yfinance 条目 |

### 二、Alpha Vantage 财报加 `reportedDate` 过滤

**改动原因**：`get_balance_sheet`、`get_cashflow`、`get_income_statement` 已有 `curr_date` 参数但未使用。现在启用该参数，按 `reportedDate <= curr_date` 过滤，只返回在回测日期之前已公开披露的财报。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | 新增 `_filter_by_reported_date()` 工具函数；三个财报函数在返回前调用过滤 |

### 三、`get_insider_transactions` 加日期截断 + limit

**改动原因**：yfinance 返回全部历史内幕交易记录，可能包含回测日期之后的数据；且数据量可能很大浪费 token。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/y_finance.py` | `get_insider_transactions` 新增 `curr_date` 参数（按 `Start Date` 过滤）和 `limit=20`（只返回最近 20 条） |
| `tradingagents/agents/utils/news_data_tools.py` | tool 层 `get_insider_transactions` 新增 `curr_date` 参数并透传 |

### 四、变更后 vendor 映射

| 工具 | 可用 vendor |
|------|------------|
| `get_balance_sheet` | `alpha_vantage` |
| `get_cashflow` | `alpha_vantage` |
| `get_income_statement` | `alpha_vantage` |
| `get_insider_transactions` | `yfinance` |

---

## 版本：v0.6.0 — 引入 FMP 替换 get_fundamentals，支持历史基本面数据

**改动日期**：2026-04-04  
**改动摘要**：`get_fundamentals` 原先调用 Alpha Vantage OVERVIEW 端点，只返回当前快照，回测时产生数据泄漏。引入 Financial Modeling Prep (FMP) 作为新数据源，每个 ticker 一次请求拉取全部历史季度数据并缓存到本地，回测时按 `curr_date` 过滤返回对应时间点的基本面指标。

---

### 一、新增 FMP 数据源

**新增原因**：Alpha Vantage OVERVIEW 端点无日期参数，始终返回"今天"的 P/E、ROE 等指标。FMP 的 `key-metrics`、`ratios`、`analyst-estimates`、`grade` 端点均返回完整历史季度数据，天然支持回测日期过滤。

**使用的 FMP 端点**：

| 端点 | 返回内容 |
|------|----------|
| `GET /api/v3/key-metrics/{symbol}?period=quarter` | 历史 P/E, P/B, EPS, BookValue, ROE, ROA, MarketCap, EV 等估值与盈利指标 |
| `GET /api/v3/ratios/{symbol}?period=quarter` | 历史 ProfitMargin, OperatingMargin, DebtToEquity, CurrentRatio 等财务比率 |
| `GET /api/v3/analyst-estimates/{symbol}` | 历史分析师预估（EPS/Revenue estimates） |
| `GET /api/v3/grade/{symbol}` | 历史评级变更（upgrades/downgrades） |
| `GET /api/v3/profile/{symbol}` | 公司静态信息（Sector, Industry, Beta） |

**本地缓存策略**：每个 ticker × 每个端点缓存为一个 JSON 文件（如 `AAPL_key-metrics.json`），首次调用后后续回测直接读取本地缓存，不消耗 API 额度。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/fmp_common.py` | **新增** — FMP 通用请求层（API Key 管理、请求发送、rate limit 异常处理） |
| `tradingagents/dataflows/fmp_fundamentals.py` | **新增** — 核心逻辑：5 个端点数据拉取、本地 JSON 缓存、按 `curr_date` 日期过滤、格式化报告输出 |

### 二、派生字段补全

除 FMP 直接提供的字段外，额外计算了 8 个派生字段以完全覆盖原 Alpha Vantage OVERVIEW 的全部信息：

| 字段 | 计算方式 |
|------|----------|
| QuarterlyEarningsGrowthYOY | 对比最近季度 vs 去年同季度的 `netIncomePerShare` |
| QuarterlyRevenueGrowthYOY | 对比最近季度 vs 去年同季度的 `revenuePerShare` |
| ForwardPE | 从 peRatio 反推价格，除以 `estimatedEpsAvg` |
| 52WeekHigh / 52WeekLow | 通过 `route_to_vendor("get_stock_data")` 获取 1 年价格历史，取 max/min |
| 50DayMovingAverage | 最近 50 日收盘价均值 |
| 200DayMovingAverage | 最近 200 日收盘价均值 |

### 三、移除 Alpha Vantage OVERVIEW

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | 移除 `get_fundamentals()` 函数（OVERVIEW 端点不再使用） |
| `tradingagents/dataflows/alpha_vantage.py` | 移除 `get_fundamentals` 导出 |

### 四、Vendor 路由更新

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | `get_fundamentals` vendor 从 `alpha_vantage` 替换为 `fmp`；新增 `fmp` 到 `VENDOR_LIST`；fallback 逻辑新增 `FMPRateLimitError` 处理 |
| `tradingagents/default_config.py` | `fundamental_data` 默认 vendor 从 `yfinance` 改为 `fmp` |

### 五、配置与环境

| 文件 | 操作 |
|------|------|
| `.env.example` | 新增 `FMP_API_KEY` 说明及申请链接 |
| `.gitignore` | 新增 `**/fmp_cache/` |

### 六、变更后 vendor 映射

| 工具 | 可用 vendor |
|------|------------|
| `get_fundamentals` | `fmp`（原 `alpha_vantage` 已移除） |
| `get_balance_sheet` | `alpha_vantage` |
| `get_cashflow` | `alpha_vantage` |
| `get_income_statement` | `alpha_vantage` |

### 七、字段覆盖率

对比原 Alpha Vantage OVERVIEW 的 ~48 个字段：直接覆盖 36 个，可推算 8 个（已实现），仅 4 个无关紧要的元数据字段缺失（FiscalYearEnd、DividendDate、ExDividendDate、AnalystTargetPrice）。**回测核心的估值与盈利指标 100% 覆盖**。

### 八、未受影响

- `fundamentals_analyst.py` 无需修改 — 工具接口 `get_fundamentals(ticker, curr_date)` 完全不变
- `get_balance_sheet`、`get_cashflow`、`get_income_statement` 仍走 Alpha Vantage，不受影响
- 下游所有消费 `fundamentals_report` 的节点（researcher、trader、debator）无需改动

---

## 版本：v0.7.0 — 批量预拉取缓存（Bulk Prefetch Cache）

**改动日期**：2026-04-04  
**改动摘要**：将按请求缓存（每次 API 调用单独存一份文件）重构为批量预拉取 + 本地切片策略。首次请求时一次性拉取 5 年完整数据存到本地，后续查询从本地按日期切片返回，零 API 调用。覆盖全部 8 个数据工具，包括新闻数据。

---

### 一、新增批量缓存模块

**新增原因**：原有按请求缓存策略下，同一 ticker 的不同日期范围各存一份文件，重复调用 API 且缓存命中率低。回测场景中同一 ticker 会被反复查询不同日期窗口，需要一次性拉取全量数据。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/bulk_cache.py` | **新增** — 批量缓存核心模块，提供 `bulk_has`/`bulk_load`/`bulk_save`（支持 `.csv`/`.txt` 扩展名）、`strip_comment_header`、`slice_csv_by_range`、`slice_csv_before`、`slice_json_news`、`bulk_clear` |

**目录结构**：
```
data_cache/bulk/
  AAPL/
    stock_data.csv          # 5 年日线 OHLCV
    stock_data.meta.json    # 记录拉取范围
    indicator_rsi.csv       # 技术指标
    balance_sheet_quarterly.csv
    news.txt                # JSON 格式新闻
    news.meta.json
  _GLOBAL/
    global_news.txt
```

### 二、数据路由重构

**改动原因**：`route_to_vendor()` 需新增批量缓存层，优先级为：批量缓存 → 按请求缓存（降级） → 调用 vendor API。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 新增 `BULK_CACHE_METHODS` 集合（8 个方法）；新增 `_prefetch_range()`、`_try_bulk_cache()` 调度器；新增 8 个批量处理函数（`_bulk_stock_data`、`_bulk_indicators`、`_bulk_balance_sheet`、`_bulk_cashflow`、`_bulk_income_statement`、`_bulk_insider_transactions`、`_bulk_news`、`_bulk_global_news`）；新增 `_is_valid_news_response()` 验证函数 |

### 三、新闻缓存特殊处理

**设计决策**：新闻缓存以牺牲服务器端相关性排序（`sort=RELEVANCE`）为代价，预拉取时改用 `sort=LATEST, limit=1000`。后续查询从本地按 `time_published` 时间戳切片。

- 空切片（缓存不覆盖请求日期范围）自动降级到直接 API 调用
- API 错误响应不会被错误缓存（`_is_valid_news_response()` 验证）
- 全局新闻预拉取限制 30 天范围（AV API 不支持过大日期跨度）

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_news.py` | `get_news()`、`get_global_news()` 新增 `sort` 参数（默认 `RELEVANCE`） |

### 四、配置变更

| 文件 | 操作 |
|------|------|
| `tradingagents/default_config.py` | 新增 `bulk_cache_enabled: True`、`bulk_cache_prefetch_years: 5`；移除重复的 `data_cache_dir` 定义 |
| `tradingagents/dataflows/local_cache.py` | `list_cache()` glob 模式从 `*.txt` 改为 `*`（跳过 `.meta.json`）；`get_cache_summary()` 分别报告 bulk 与 per-request 统计 |

### 五、运行时修复

| 文件 | 问题 | 修复 |
|------|------|------|
| `tradingagents/agents/utils/agent_states.py` | `sentiment_report` 字段缺少缩进导致 `IndentationError` | 补全 4 空格缩进 |
| `tradingagents/graph/trading_graph.py` | Windows GBK 终端无法显示 LLM 输出中的 emoji | `pretty_print()` 外加 `UnicodeEncodeError` 捕获，降级为 ASCII 输出 |

### 六、批量缓存方法清单

| 方法 | 预拉取策略 | 切片方式 |
|------|-----------|----------|
| `get_stock_data` | 5 年日线 | `slice_csv_by_range(start, end)` |
| `get_indicators` | 5 年指标 | `slice_csv_by_range(curr_date - lookback, curr_date)` |
| `get_balance_sheet` | 全量（不传 curr_date） | `slice_csv_before(curr_date)` |
| `get_cashflow` | 全量 | `slice_csv_before(curr_date)` |
| `get_income_statement` | 全量 | `slice_csv_before(curr_date)` |
| `get_insider_transactions` | 全量 | `slice_csv_before(curr_date)` |
| `get_news` | `limit=1000, sort=LATEST` | `slice_json_news(start, end, limit=30)` |
| `get_global_news` | 最近 30 天, `limit=1000` | `slice_json_news(start, end, limit)` |

---

## 版本：v0.8.0 — 用 Alpha Vantage 替换 FMP 实现 get_fundamentals

**改动日期**：2026-04-05  
**改动摘要**：FMP 免费版不支持 `key-metrics` 端点（返回 403 Forbidden），导致 `get_fundamentals` 完全不可用。改用 Alpha Vantage 的 BALANCE_SHEET、INCOME_STATEMENT、CASH_FLOW、EARNINGS 端点，结合股价数据推算全部估值/盈利/偿债指标。移除不支持回测的功能（公司简介、分析师评级等）。

---

### 一、新增 Alpha Vantage 综合基本面模块

**新增原因**：FMP 免费版（Free Plan）不支持 `key-metrics` 和 `ratios` 端点（需 Starter Plan $22/月），而用户已开通 Alpha Vantage 会员。AV 的四个财报端点提供完整历史季度数据，可推算出 FMP 版报告中的绝大部分指标。

**使用的 AV 端点**：

| 端点 | 返回内容 | 缓存格式 |
|------|----------|----------|
| `BALANCE_SHEET` | 历史季度资产负债表（totalAssets, totalEquity, shares, debt 等） | JSON |
| `INCOME_STATEMENT` | 历史季度利润表（revenue, netIncome, grossProfit, ebitda 等） | JSON |
| `CASH_FLOW` | 历史季度现金流量表（operatingCashflow, capitalExpenditures 等） | JSON |
| `EARNINGS` | 历史季度 EPS（reportedEPS, estimatedEPS, surprise, surprisePercentage） | JSON |

**缓存策略**：采用 FMP 同款 `_fetch_and_cache` 模式，每个 ticker × 每个端点一份 JSON 文件（如 `data_cache/bulk/AAPL/balance_sheet.json`），首次调用后永久缓存。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals_full.py` | **新增** — 核心实现：JSON 缓存、按 curr_date 日期过滤、指标计算、格式化报告 |

### 二、计算指标覆盖

从 AV 财报数据 + 股价推算的指标：

| 分区 | 指标 | 计算公式 |
|------|------|----------|
| **Valuation** | Market Cap | 股价 × commonStockSharesOutstanding |
| | P/E (TTM) | 股价 / (TTM netIncome / shares) |
| | P/B | 股价 / (totalShareholderEquity / shares) |
| | P/S | MarketCap / TTM totalRevenue |
| | EV/EBITDA | (MCap + debt − cash) / TTM ebitda |
| | P/FCF | MCap / TTM (operatingCashflow − capex) |
| **Per-Share** | EPS, Revenue/Share, Book Value/Share, FCF/Share | 对应项 / shares |
| **Profitability** | Gross/Operating/Net Margin | 对应项 / totalRevenue |
| | ROE | TTM netIncome / totalShareholderEquity |
| | ROA | TTM netIncome / totalAssets |
| **Financial Health** | Debt/Equity, Current Ratio, Quick Ratio, Interest Coverage, Cash/Share | 标准公式 |
| **Growth** | Earnings/Revenue Growth YOY | 本季 vs 去年同季 |
| **Market Data** | 52W High/Low, 50/200 DMA | 从 stock_data 计算 |
| **Earnings** | Reported/Estimated EPS, Surprise | 来自 EARNINGS 端点 |

### 三、移除的功能

以下 FMP 版功能因不支持回测或无 AV 等价端点而移除：

| 移除项 | 原因 |
|--------|------|
| Company Profile（名称、行业、描述） | 来自 OVERVIEW 端点，不支持回测 |
| Beta | 来自 OVERVIEW，不支持回测 |
| Analyst Ratings / Grades | FMP `grade` 端点无 AV 等价 |
| Forward P/E、PEG | 需前瞻性 analyst estimates，AV EARNINGS 仅有历史 EPS |
| Dividends（Yield, Payout Ratio） | 无可靠历史数据源 |

### 四、防数据泄漏

- **EARNINGS 端点**：按 `reportedDate`（实际披露日期）过滤，严格防止泄漏
- **财报端点**：按 `fiscalDateEnding` 过滤（AV 不提供 reportedDate）
- **股价数据**：通过已有 bulk cache 获取，按 curr_date 切片

### 五、Vendor 路由更新

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | `get_fundamentals` vendor 从 `fmp` 替换为 `alpha_vantage`；移除 `fmp_fundamentals` import |
| `tradingagents/default_config.py` | `fundamental_data` 默认 vendor 从 `fmp` 改为 `alpha_vantage` |
| `main.py` | vendor 配置同步更新 |

### 六、变更后 vendor 映射

| 工具 | 可用 vendor |
|------|------------|
| `get_fundamentals` | `alpha_vantage`（原 `fmp` 已移除） |
| `get_balance_sheet` | `alpha_vantage` |
| `get_cashflow` | `alpha_vantage` |
| `get_income_statement` | `alpha_vantage` |

### 七、未受影响

- `fundamental_data_tools.py` — 工具接口 `get_fundamentals(ticker, curr_date)` 完全不变
- `fundamentals_analyst.py` — Agent prompt 与工具绑定不变
- `fmp_fundamentals.py` / `fmp_common.py` — 保留文件不删，仅不再注册为 vendor
- 下游所有消费 `fundamentals_report` 的节点（researcher、trader、debator）无需改动

---

## 版本：v0.9.0 — 统一 Alpha Vantage 数据源 + 修复指标缓存

**改动日期**：2026-04-05  
**改动摘要**：将 `core_stock_apis` 和 `technical_indicators` 从 yfinance 切换到 Alpha Vantage，消除冗余数据拉取；修复指标批量缓存存���格式错误导致切片失败的问题；修复 `TIME_SERIES_DAILY_ADJUSTED` 和 `MACD` 两个 premium 端点问题

---

### 一、统一数据源到 Alpha Vantage

**改动原因**：yfinance 和 Alpha Vantage 同时作为股价/指标数据源，导致同一 ticker 缓存两份数据（`NVDA-YFin-indicators.csv` 和 `stock_data.csv`）。统一使用 Alpha Vantage 减少 API 调用和存储浪费。

| 文件 | 操作 |
|------|------|
| `tradingagents/default_config.py` | `core_stock_apis`: `yfinance` �� `alpha_vantage`；`technical_indicators`: `yfinance` → `alpha_vantage` |
| `main.py` | ��步更新 vendor 配置 |

### 二���修复 Premium 端点问题

#### 2.1 `TIME_SERIES_DAILY_ADJUSTED` → `TIME_SERIES_DAILY`

**问题**：`TIME_SERIES_DAILY_ADJUSTED` 为 AV 高级端点，用户订阅等级不支持。  
**修复**：改用功能等价的 `TIME_SERIES_DAILY`（��含 adjusted close 和 split/dividend 列，回测���景不需要）。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_stock.py` | `_make_api_request("TIME_SERIES_DAILY_ADJUSTED", ...)` → `_make_api_request("TIME_SERIES_DAILY", ...)` |

#### 2.2 `MACD` → `MACDEXT`

**问题**��`MACD` 技术指标端点为 AV 高级端��，始终返回 premium error。  
**修复**：改用 `MACDEXT`（Extended MACD），返回完全相同的列（`MACD`, `MACD_Signal`, `MACD_Hist`），���在用户订阅等级下可用。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_indicator.py` | 三处 `_make_api_request("MACD", ...)` �� `_make_api_request("MACDEXT", ...)` |
| `tradingagents/dataflows/interface.py` | `_INDICATOR_MAP` 中 macd/macds/macdh 的 `av_func` �� `"MACD"` → `"MACDEXT"` |

### 三、修复指标批量缓存

**问题**：`_bulk_indicators` 调用 `get_indicator()` 获取数据，但该函数返回的是已格式化的 `date: value` 文本（含描述信息），存为 `.csv` 后 `slice_csv_by_range()` ��法解析，导致所��指标缓存切片返回空数据。

**修复**：重写 `_bulk_indicators`，绕过 `get_indicator()` 的格式化逻辑，直接调用 `_make_api_request()` 获取 AV 原始 CSV 数据存入缓存。切片后再转换为 `date: value` 格式输出。

**新增特性**：
- MACD 三指标（macd, macds, macdh）共享同一缓存文件 `indicator_raw_macd.csv`
- Bollinger Bands 三��标（boll, boll_ub, boll_lb）共享同一缓存文件 `indicator_raw_bbands.csv`
- 每个指标组仅需一次 API 调用，6 个指标组覆盖全部 11 个指标���VWMA 除外，AV 不���持）
- 存入前校验响应包含 `time` 列头，防止错误响应被缓存

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 重写 `_bulk_indicators()`：新增 `_INDICATOR_MAP`（指标→AV API 映射）和 `_INDICATOR_DESCRIPTIONS`；改为直接调 `_make_api_request()` 获取原始 CSV |

### 四、缓存文件结构变更

旧结构（已废弃）：
```
data_cache/bulk/NVDA/
  indicator_close_50_sma.csv    # 格式化文本，无法切片
  indicator_macd.csv            # 错误响应
```

新���构：
```
data_cache/bulk/NVDA/
  indicator_raw_sma_50.csv      # 原始 CSV (time,SMA)
  indicator_raw_sma_200.csv     # 原始 CSV (time,SMA)
  indicator_raw_ema_10.csv      # 原始 CSV (time,EMA)
  indicator_raw_macd.csv        # 原始 CSV (time,MACD,MACD_Hist,MACD_Signal)
  indicator_raw_rsi.csv         # 原始 CSV (time,RSI)
  indicator_raw_bbands.csv      # 原始 CSV (time,Real Lower Band,Real Middle Band,Real Upper Band)
  indicator_raw_atr.csv         # 原始 CSV (time,ATR)
```

### 五、清理旧缓存

删除所有旧格式 `indicator_*.csv` 缓存文件及对应 `.meta.json`，由新逻辑��新拉取原始 CSV。yfinance 产生的冗余缓存文件（`NVDA-YFin-indicators.csv` 等）一并清理。

### 六、EPS Surprise 显示修复

**问题**：`alpha_vantage_fundamentals_full.py` 中 EPS Surprise % ���用 `_fmt(value, 'pct')` 格式化（×100），但 AV `surprisePercentage` 已是百分比值，导致显示值放大 100 ��（如 11.93% ��示为 1193.06%）。  
**修复**：改用 `_fmt(value, 'ratio')` 格式化（不×100）。

| ��件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals_full.py` | `_fmt(m.get('eps_surprise_pct'), 'pct')` → `_fmt(m.get('eps_surprise_pct'), 'ratio')` |

---

## 版本：v0.10.0 — 完善 Bulk Cache 体系 + 移除 FMP + 数据完整性校验

**改动日期**：2026-04-05  
**改动摘要**：修复财报 JSON→CSV 转换、insider 切换到 AV、分段新闻拉取覆盖 5 年、移除 FMP 数据源、统一 bulk cache 路由（取消按请求缓存降级）、加固存储前校验、修复 fundamentals 空 ticker bug

---

### 一、修复财报 Bulk Cache（JSON 存为 CSV）

**问题**：AV 的 `BALANCE_SHEET`/`INCOME_STATEMENT`/`CASH_FLOW` 端点返回 JSON，但 `_bulk_balance_sheet` 等函数直接存为 `.csv`，`slice_csv_before()` 无法解析 JSON 格式数据，静默返回全部数据——**回测数据泄漏**。

**修复**：在 `alpha_vantage_fundamentals.py` 中新增 `_json_fundamentals_to_csv(raw, freq)` 函数，将 JSON 的 `quarterlyReports`/`annualReports` 数组转为 CSV，确保 `fiscalDateEnding` 为第一列。三个 `get_*` 函数在 `_make_api_request` 之后插入此转换。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals.py` | 新增 `_json_fundamentals_to_csv()`；修改 `get_balance_sheet()`、`get_cashflow()`、`get_income_statement()` |

### 二、Insider Transactions 切换到 Alpha Vantage

**问题**：yfinance 只返回最近 20 条 insider 交易（约 2 个月），无法支持回测。

**修复**：重写 `_bulk_insider_transactions()`，直接调用 AV `INSIDER_TRANSACTIONS` API，解析 JSON 转 CSV 存储。AV 返回 6000+ 条记录（覆盖 20+ 年）。查询时限制返回最近 50 条，防止撑爆 LLM 上下文。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 重写 `_bulk_insider_transactions()`；新增 `alpha_vantage` vendor 条目；返回限制 50 条 |

### 三、分段新闻拉取覆盖 5 年

**问题**：单次 `limit=1000` 请求，热门股票 10 天内即超 1000 篇上限，实际只覆盖约 10 天。

**修复**：
- 新增 `_generate_date_segments()` 和 `_segmented_news_fetch()` 工具函数
- Ticker 新闻：5 天一段（365 段），合并去重（按 URL）
- 全局新闻：15 天一段（约 122 段）
- 每段间隔 1 秒（用户有 AV Premium 75 req/min）

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 新增 `_generate_date_segments()`、`_segmented_news_fetch()`；重写 `_bulk_news()`、`_bulk_global_news()` |

### 四、移除 FMP 数据源

**原因**：`get_fundamentals` 已有完整的 AV 实现（`alpha_vantage_fundamentals_full.py`），FMP 代码不再需要。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/fmp_common.py` | **删除** |
| `tradingagents/dataflows/fmp_fundamentals.py` | **删除** |
| `tradingagents/dataflows/interface.py` | 移除 `FMPRateLimitError` 导入和引用；移除 `"fmp"` vendor 条目 |

### 五、统一 Bulk Cache 路由，取消降级

**问题**：`BULK_CACHE_METHODS` 中的方法在 bulk cache 返回 `None` 时，会降级到按请求缓存（`load_cache`/`save_cache`），产生多余的 `get_fundamentals/`、`get_indicators/`、`get_stock_data/` 目录。

**修复**：
- `route_to_vendor` 中 bulk cache 方法不再降级，返回 `None` 即表示数据不可用
- `get_fundamentals` 加入 `BULK_CACHE_METHODS`，新增 `_bulk_fundamentals()` 直接透传到 vendor（内部从 `bulk/{TICKER}/*.json` 读取）
- 所有数据统一走 `data_cache/bulk/` 目录，不再产生按请求缓存文件

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | `route_to_vendor` 取消降级逻辑；`BULK_CACHE_METHODS` 新增 `get_fundamentals`；新增 `_bulk_fundamentals()` |

### 六、加固存储前校验

**问题**：API 返回错误响应（JSON 错误信息）被当作有效数据存入 bulk cache，导致缓存被污染。

**修复**：在 `bulk_save` 之前检查关键列头：
- `_bulk_stock_data`：检查 `timestamp` 列
- `_bulk_balance_sheet`/`_bulk_cashflow`/`_bulk_income_statement`：检查 `fiscalDateEnding` 列
- 校验失败时返回 `None`，不存入缓存

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/interface.py` | 4 个 `_bulk_*` 函数新增列头校验 |

### 七、修复 Fundamentals 空 Ticker Bug

**问题**：`_compute_price_derived()` 用 `bs.get("symbol", "")` 获取 ticker，当 `bs` 为空 dict 时传入空字符串，导致 AV 返回 "Invalid API call" 错误，影响估值指标计算。

**修复**：`_compute_metrics` 新增 `ticker` 参数，`_compute_price_derived` 优先使用传入的 ticker。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_fundamentals_full.py` | `_compute_metrics` 新增 `ticker` 参数；`_compute_price_derived` 改用 `ticker or bs.get("symbol", "")` |

### 八、新增缓存验证脚本

新增 `verify_cache.py`，遍历 `data_cache/bulk/` 下所有文件，按类型执行完整性检查（CSV 列头、JSON 结构、行数、日期范围），输出 PASS/FAIL/WARN 报告。

### 九、已缓存 Ticker

| Ticker | 新闻数 | Insider 数 | 分段截断 |
|--------|--------|-----------|---------|
| NVDA | 17,677 | 6,891 | 2 段 |
| AAPL | 8,192 | 7,096 | 0 段 |
| MSFT | 15,071 | 1,234 | 1 段 |
| META | 4,289 | 22,430 | 0 段 |
| GOOGL | 10,144 | 13,919 | 0 段 |

---

## 版本：v0.10.1 — 辩论阶段报告重复注入优化

**改动日期**：2026-04-06  
**改动摘要**：Bull/Bear 辩手和风险辩论三方每轮调用都从 state 重新取四份完整报告拼入 prompt，报告内容不变却随轮次线性重复。改为仅在第一轮（`count == 0`）注入完整报告，后续轮次只注入 `history`，减少冗余 token。

---

### 改动内容

**改动原因**：`history` 字段本身已累积所有历史发言，后续轮次重复注入四份完整报告（市场/情绪/新闻/基本面）纯属冗余。默认 1 轮配置下影响有限，辩论轮数增大时收益显著。

| 文件 | 改动 |
|------|------|
| `tradingagents/agents/researchers/bull_researcher.py` | `count == 0` 时注入完整四份报告，后续轮次只注入 `past_memory_str` |
| `tradingagents/agents/researchers/bear_researcher.py` | 同上 |
| `tradingagents/agents/risk_mgmt/aggressive_debator.py` | `count == 0` 时注入完整四份报告，后续轮次跳过（`trader_decision` 每轮保留） |
| `tradingagents/agents/risk_mgmt/conservative_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/neutral_debator.py` | 同上 |

**注**：风险辩论的 `trader_decision` 每轮保留注入，因其是辩论的核心依据且内容较短。

---

## 版本：v0.11.0 — Sentiment Analyst 增强 + Macro Analyst 新增

**改动日期**：2026-04-06  
**改动摘要**：为 Sentiment Analyst 新增量化情绪工具（AV 新闻情绪汇总 + VIX）；新增 Macro Analyst Agent，接入 7 个宏观指标数据工具；修复 yfinance 并发下载数据交叉 Bug。

---

### 一、Sentiment Analyst 增强

**问题**：原 Sentiment Analyst 只能通过 `get_news` 读取原始新闻标题，无量化情绪数据，LLM 需自行解读。

**新增内容**：
- 新增 `get_sentiment_summary` 工具：解析 bulk cache 中 AV NEWS_SENTIMENT 数据，按日汇总情绪评分（均值、Bullish/Neutral/Bearish 计数），输出 Markdown 表格
- 新增 `get_vix` 工具：通过 yfinance 获取 VIX 历史日数据，反映市场恐惧/贪婪情绪
- 将新闻条数上限从 30 提升至 100
- 更新 Sentiment Analyst prompt，明确三步工作流：先调 `get_sentiment_summary` 量化评分 → `get_vix` 市场情绪 → `get_news` 原文细节

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/sentiment_utils.py` | 新增 `get_sentiment_summary()` |
| `tradingagents/agents/utils/sentiment_tools.py` | 新建，封装 `get_sentiment_summary` 和 `get_vix` 两个 `@tool` |
| `tradingagents/dataflows/y_finance.py` | 新增 `get_vix_data()` |
| `tradingagents/agents/analysts/sentiment_analyst.py` | 更新 tools 列表和 prompt |
| `tradingagents/dataflows/interface.py` | 新闻切片 `limit` 从 30 改为 100 |

---

### 二、Macro Analyst 新增

**问题**：原系统缺少宏观视角，无法分析利率、通胀、GDP 等宏观环境对目标股票的影响。

**新增内容**：
- 新增 **Macro Analyst Agent**，常驻于分析师序列（无需手动选中）
- 接入 7 个数据工具：联邦基金利率、CPI、实际 GDP、失业率、10 年期国债收益率（Alpha Vantage Premium）+ 美元指数 DXY、VIX（yfinance）
- Prompt 明确分析框架：货币政策 → 通胀 → 经济增长 → 就业 → 市场情绪 → 汇率，最终输出 Tailwind/Neutral/Headwind 判断及汇总表
- 新增 `macro_report` 字段到 `AgentState`

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/alpha_vantage_macro.py` | 新建，实现 5 个 AV 宏观端点函数 |
| `tradingagents/dataflows/y_finance.py` | 新增 `get_dxy_data()` |
| `tradingagents/agents/utils/macro_tools.py` | 新建，封装 6 个宏观 `@tool`（含 local_cache） |
| `tradingagents/agents/utils/agent_states.py` | 新增 `macro_report` 字段 |
| `tradingagents/agents/analysts/macro_analyst.py` | 新建 Macro Analyst Agent |
| `tradingagents/agents/__init__.py` | 导出 `create_macro_analyst` |
| `tradingagents/graph/conditional_logic.py` | 新增 `should_continue_macro()` |
| `tradingagents/graph/trading_graph.py` | 新增 macro 工具导入和 ToolNode；默认 `selected_analysts` 包含 macro |
| `tradingagents/graph/setup.py` | 新增 macro 分支 |
| `tradingagents/graph/propagation.py` | 初始化 `macro_report: ""` |

---

### 三、修复 yfinance 并发下载数据交叉 Bug

**问题**：`get_vix_data` 和 `get_dxy_data` 均使用 `yf.download()`。LangGraph ToolNode 在同一批次中并发执行多个工具时，`yf.download()` 的内部共享状态（session/响应缓冲）导致两个函数的返回值互相交叉——DXY 返回 VIX 数据，VIX 返回 DXY 数据，且每次运行必现。

**修复**：将两个函数的下载方式从 `yf.download(ticker, ...)` 改为 `yf.Ticker(ticker).history(...)`。`Ticker` 对象独立实例化，不共享内部状态，并发安全。

| 文件 | 操作 |
|------|------|
| `tradingagents/dataflows/y_finance.py` | `get_vix_data` 和 `get_dxy_data` 改用 `yf.Ticker.history()` |

---

## 版本：v0.4.0 — 节点职能改造 + 结构化输出 + 回测引擎

**改动日期**：2026-04-07  
**改动摘要**：重新划分各决策节点职能（RM 方向决策、Trader 量化规划、PM 最终指令），三个决策节点接入 Pydantic 结构化输出，风险辩论从定性改为定量，新增持仓追踪系统和日线级别回测引擎。

---

### 一、决策节点职能重新划分

**改动前**：Research Manager 既做方向判断又制定投资计划，Trader 仅评估可行性，PM 做 5 级评级（Buy/Overweight/Hold/Underweight/Sell），职责重叠。

**改动后**：

| 节点 | 模型 | 职责 |
|------|------|------|
| Research Manager | Deep | 方向决策：只输出 Buy/Sell/Hold + 核心理由 |
| Trader | Deep（原为 Quick） | 执行规划：目标仓位%、止盈价、止损价 |
| PM | Deep | 最终拍板：综合风险辩论，输出可执行指令 |

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/managers/research_manager.py` | 删除投资计划制定，聚焦方向性决策，注入持仓状态 |
| `tradingagents/agents/trader/trader.py` | 完全重写为执行规划者，解析 RM 的 JSON 决策，输出量化参数 |
| `tradingagents/agents/managers/portfolio_manager.py` | 评级从 5 级简化为 3 级，解析 Trader JSON，注入持仓状态 |
| `tradingagents/graph/setup.py` | Trader 的 LLM 从 `quick_thinking_llm` 切换为 `deep_thinking_llm` |

---

### 二、结构化输出（Pydantic Schema + 重试机制）

**改动前**：三个决策节点输出自由文本，需要 LLM 二次解析提取信号。

**改动后**：通过 `with_structured_output(schema, method="json_schema")` 约束输出，Pydantic `model_validator` 校验 SL/TP 一致性，`invoke_structured()` 辅助函数实现校验失败反馈重试 + 网络异常指数退避。

**Schema 定义**：
- `ResearchManagerDecision`：action + reasoning
- `TraderDecision`：action + target_position_pct + take_profit_price + stop_loss_price + reasoning
- `PortfolioManagerDecision`：同 TraderDecision

**Pydantic 校验规则**：
- `stop_loss_price > 0`，`take_profit_price > 0`
- `stop_loss_price < take_profit_price`

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/utils/schemas.py` | 新建，3 个 Pydantic schema + `invoke_structured()` 辅助函数 |
| `tradingagents/graph/signal_processing.py` | 优先 `json.loads()` 提取 action，失败时回退 LLM 解析；评级从 5 级改为 3 级 |

---

### 三、风险辩论定量化

**改动前**：激进/保守/中性三方做定性辩论（"风险太大"/"值得投资"）。

**改动后**：三方围绕 Trader 给出的具体参数（仓位比例、止盈/止损价位）展开定量辩论：
- 激进方：主张更大仓位、更高止盈、更宽止损
- 保守方：主张更小仓位、更低止盈、更紧止损
- 中性方：平衡两方，评估参数合理性

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/risk_mgmt/aggressive_debator.py` | 解析 Trader JSON，围绕具体参数辩论 |
| `tradingagents/agents/risk_mgmt/conservative_debator.py` | 同上 |
| `tradingagents/agents/risk_mgmt/neutral_debator.py` | 同上 |

---

### 四、持仓状态注入

**改动前**：每次 `propagate()` 无持仓上下文，agent 不知道当前仓位情况。

**改动后**：AgentState 新增 7 个持仓字段，由回测引擎每日注入，各决策节点在 prompt 中读取持仓信息辅助决策。

| 字段 | 含义 |
|------|------|
| `current_position_pct` | 当前仓位占总资金比例 0-100% |
| `avg_cost` | 持仓均价 |
| `total_capital` | 账户总资产 |
| `current_stop_loss` | 当前止损价 |
| `current_take_profit` | 当前止盈价 |
| `last_action` | 上一次操作 Buy/Sell/Hold |
| `unrealized_pnl_pct` | 未实现盈亏百分比 |

| 文件 | 操作 |
|------|------|
| `tradingagents/agents/utils/agent_states.py` | AgentState 新增 7 个持仓字段 |
| `tradingagents/graph/propagation.py` | `create_initial_state()` 支持 `position_state` 参数注入 |
| `tradingagents/graph/trading_graph.py` | `propagate()` 新增 `position_state` 参数 |

---

### 五、回测引擎

**新增模块** `tradingagents/backtesting/`，实现日线级别回测：

**每日流程**：
1. 开盘：以开盘价执行前一日 PM 指令
2. 盘中：用当日高低价检查止盈/止损是否触发（止损优先）
3. 收盘：更新持仓数据，注入 agent state，运行完整 pipeline
4. 保存 PM 输出，留待次日执行

**引擎侧 SL/TP Sanity Check**：止损价必须低于当前价，止盈价必须高于当前价，否则丢弃。防止模型输出荒谬值导致错误触发。

| 文件 | 操作 |
|------|------|
| `tradingagents/backtesting/__init__.py` | 新建，导出 PositionTracker 和 BacktestEngine |
| `tradingagents/backtesting/position.py` | 新建，持仓管理（下单执行、止盈止损检查、状态导出） |
| `tradingagents/backtesting/engine.py` | 新建，日循环回测引擎，从 bulk cache 读取 OHLC 数据 |
| `main.py` | 改为回测模式入口 |

---

### 六、可视化与指标计算

**新增** `visualize_backtest.py`，从回测结果 JSON 生成 4 面板图表（净值曲线、回撤、仓位、交易活动）+ 计算关键指标（CAGR、波动率、夏普比率、最大回撤、换手率、交易成本），并与 Buy & Hold 基准对比。

---

### 七、Bug 修复

1. **Recursion limit 过紧**：5 个分析师 + 两轮辩论的总节点调用容易超过 100 次上限，改为 200。
2. **SL/TP 错误触发**：模型偶尔输出止损价高于市价的荒谬值，导致盘中必定触发止损。新增 Pydantic 层校验（SL < TP）和引擎层校验（SL < 当前价，TP > 当前价）双重防护。

| 文件 | 操作 |
|------|------|
| `tradingagents/graph/propagation.py` | `max_recur_limit` 从 100 改为 200 |
| `tradingagents/agents/utils/schemas.py` | 新增 `model_validator` 校验 SL < TP 且均为正值 |
| `tradingagents/backtesting/position.py` | `execute_order` 新增 SL/TP vs 市价 sanity check |

---

