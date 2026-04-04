分析师步骤其实偏向：编排式工作流

当前的multi-agent的设计是decentralized

在各个环节注意中间件设计，确保大模型按需求做事不跑偏不幻觉输出结构正确

全程注意推理三明治
### 对比基准

多 agent bot 必须与以下基准进行对比：

- **Buy-and-Hold**：基准指数或 ETF
- **单 agent bot**：无辩论 / 无多角色的原始 TradingAgents
- **传统量化策略**：如动量策略或基于 RSI 的规则策略

### 评估指标

| 指标 | 说明 |
|------|------|
| 年化收益率（Annualized Return / CAGR） | 测试期间的复合年增长率 |
| 波动率（Volatility） | 收益率的标准差 |
| 夏普比率（Sharpe Ratio） | 收益 / 波动率，衡量风险调整后的收益 |
| 最大回撤（Max Drawdown） | 从历史最高点到最低点的最大跌幅 |
| 换手率（Turnover） | 持仓随时间变化的频率或幅度 |
| 交易成本（Transaction Costs） | 交易带来的总成本影响 |

### guideline写明建议

以下方向可获得额外加分：

- **新增 Agent 角色**：如基于宏观经济数据发布的宏观事件预测 agent
- **滚动前向验证（Roll-forward Validation）**：优化滚动窗口以降低过拟合
- **Retrieval Augmented Prompts**：通过向量库注入结构化外部数据
- **多资产组合**：将 TradingAgents 扩展为支持组合管理，而非仅单支股票
- **加密货币市场**：扩展 TradingAgents 支持加密资产交易

### 交付物

- 修改后的 TradingAgents 代码（不能只是复制，需清晰记录改动）
- 数据收集、回测与指标计算脚本
- `requirements.txt` 或 `environment.yml`（确保环境可复现）
- 小型 demo 脚本（展示如何对指定 ticker 和日期运行 bot）
- 支持通过 config 切换模型
- 撰写研究报告并制作演示，将多 agent bot 与经典基准进行对比

# Processing
## 前期数据设计工作

**完成以下的设计即可不用具体实施，写为 spec 技术文档形式**

### 1. 确定测试品种与时间窗口

**选定配置（已写入 `main.py`）：**

| 参数 | 值 | 说明 |
|------|-----|------|
| 股票品种 | `NVDA` | NVIDIA，AI 主题龙头，波动大、新闻丰富，适合情绪 / 基本面 agent 分析 |
| 分析日期 | `2024-05-10` | 英伟达财报季前后，市场情绪复杂，测试价值高 |
| 加密品种 | `BTC` | 比特币，对应 `crypto` analyst，同一日期区间 |
| 可替换选项 | `AAPL 2024-06-15`, `MSFT 2024-07-20` | 均为主流美股，数据完整 |

**运行方式**：直接执行 `python main.py`，其中已预设 NVDA / 2024-05-10 标准配置。

**数据采集模式（结论）：**

> 采用**按需拉取（On-demand Fetch）**，而非预先建立离线数据库。
>
> - 每次运行时，各 Agent 工具函数直接调用 yfinance / CoinGecko / FRED API 获取数据（**实时拉取**）
> - 首次拉取后，数据自动写入 `./data_cache/{category}/{symbol}/{start}_{end}.parquet`（**Parquet 本地缓存**）
> - 后续再次运行时，若缓存命中则跳过 API 调用，类似"懒加载离线库"（**缓存后可离线复用**）
> - **无需预先手动建库**——缓存在 Agent 实际运行过程中自动积累
>
> 实时与离线并不矛盾：首次运行为实时，之后命中缓存即为离线。这是本项目数据层的核心设计选择。

### 2. 扩展数据源

**职责**：负责数据采集层，为 agent 提供**当日/实时**的分析输入。#3 的向量库所需历史数据也由本任务统一采集，#3 直接复用，不重复开发采集逻辑。

- **数据提供商**：从 yfinance 换成 Alpha Vantage、Tiingo、Polygon、新浪财经
- **市场覆盖**：集成港股、A 股、加密货币等市场数据接口（**教授说加密有加分，这个最好要有，别的都行**）
- **数据类型**：增加 alternative data、社交媒体情绪、宏观经济指标

**数据源参考使用**：
- **实时数据源**：
    - Alpha Vantage（免费版）：
        -- 提供股票、外汇、加密货币的实时数据。
        -- 每分钟 5 次请求限制，适合低频实时需求。
    - Tiingo（免费试用）：
        -- 提供股票和外汇的实时数据。
        -- 需要注册 API 密钥。
    - CoinGecko（加密货币）：
        -- 提供加密货币的实时价格、交易量等数据。
        -- 无需 API 密钥，完全免费。
    - 新浪财经（港股、A 股）：
        -- 提供实时行情数据，适合中国市场。
    - **采集**：
        - 职责：采集实时数据，供 Agent 在运行时分析。
        - 实现方式：
            -- 使用 WebSocket 或定时任务定期拉取实时数据。
            -- 数据源：Alpha Vantage、Tiingo、CoinGecko、新浪财经。
- **离线数据源**：
    - Yahoo Finance（yfinance）：
        -- 提供股票的历史数据和技术指标。
        -- 免费且易用，适合离线回测。
    - Quandl（现为 Nasdaq Data Link）：
        -- 提供经济指标、股票历史数据。
        -- 免费数据集有限，但适合离线分析。
    - FRED（美国经济数据）：
        -- 提供宏观经济指标（如利率、CPI）。
        -- 免费且数据质量高。
    - SEC EDGAR：
        -- 提供公司财务报告（10-K、10-Q）。
        -- 免费，适合离线分析。
    - **采集**：
        - 职责：采集历史数据，供回测和向量化检索。
        - 实现方式：
            -- 使用批量请求拉取历史数据。
            -- 数据源：yfinance、Quandl、FRED、SEC EDGAR。

---

#### ✅ 已实现方案（2026-03-28）

**原则**：免费优先、零 API Key 优先、自动缓存、#3 直接复用。

##### 数据类型与数据源选型

| 数据类别 | 数据源 | API Key | 实时/离线 | 说明 |
|----------|--------|---------|-----------|------|
| 股票 OHLCV | `yfinance` | 不需要 | 两者 | 已有，保留 |
| 技术指标 | `yfinance` / `alpha_vantage` | 可选 | 两者 | 已有，保留 |
| 基本面 | `yfinance` | 不需要 | 离线 | 已有，保留 |
| 新闻 | `yfinance` | 不需要 | 实时 | 已有，保留 |
| **加密货币** | **CoinGecko** | **不需要** | **两者** | ✅ 新增，重点实现 |
| **宏观经济** | **FRED** | **免费申请** | **离线为主** | ✅ 新增，覆盖利率/CPI/VIX |
| **新闻情绪** | **VADER on yfinance** | **不需要** | **两者** | ✅ 新增，零额外依赖 |
| **社交情绪** | **Reddit PRAW（可选）** | **免费申请** | **实时** | ✅ 新增，不填则降级为新闻情绪 |

##### 日K数据市场覆盖（2026-03-29 确认）

通过 **yfinance 一个库**，只需修改 ticker 格式即可接入以下市场，无需切换数据源：

| 市场 | Ticker 格式示例 | 状态 | 备注 |
|------|----------------|------|------|
| 美股 | `AAPL`, `NVDA` | ✅ 完整 | 主要测试品种 |
| 港股 | `0700.HK` | ✅ 可用 | 加 `.HK` 后缀 |
| A股 | `600519.SS`, `000001.SZ` | ✅ 可用 | 上证加 `.SS`，深证加 `.SZ`；部分数据有缺口 |
| 日股 | `7203.T` | ✅ 可用 | 加 `.T` 后缀 |
| 加密货币 | `BTC`（内部转为 `BTC-USD`）| ✅ 完整 | 24/7 无节假日，无市场间歇 |
| 外汇 | `EURUSD=X` | ⚠️ yfinance 支持 | 框架未封装，需时可扩展 |
| 大宗商品 | `GC=F`（黄金）, `CL=F`（原油）| ⚠️ yfinance 支持 | 同上 |

**结论**：核心测试品种（美股 + 加密货币）已完整覆盖，港股/A股可用但不作为主要测试对象。

##### 实时 vs 离线——问题回答

> **哪种方式免费且不需大量人工维护？**
> 
> - **最优选：按需拉取（On-demand Fetch）**——Agent 运行时直接调用数据函数，无需维护任何定时任务或 WebSocket 连接。yfinance / CoinGecko / FRED 均支持。
> - 定时任务/WebSocket 适合生产级系统，本项目以研究为主，按需拉取即可。

##### 历史数据存储是否必要？

> **必要，但无需数据库**——采用 Parquet 文件缓存：
> - 首次调用 → 写入 `data_cache/{category}/{symbol}/` 目录
> - 后续调用 → 命中缓存则直接返回，跳过 API 调用
> - #3 RAP 向量库直接 `load_dataframe()` 读取，无需重复采集逻辑
> - 文件结构：`data_cache/crypto/BTC/2024-01-01_2024-12-31.parquet`

##### 数据格式标准（口径一致）

所有数据函数统一返回**带 header 注释的 CSV 字符串**（与现有 yfinance 函数一致，供 LLM 直接阅读），同时在内部将 DataFrame 写入 Parquet 缓存（供 #3 使用）。

**标准列命名**（所有 OHLCV 类数据）：

```
date, open, high, low, close, volume
```

**情绪数据标准列**：

```
date, title, sentiment (POSITIVE/NEUTRAL/NEGATIVE), compound, positive, negative
```

**宏观数据标准列**：

```
date, value, series_id, description
```

##### 新增文件清单

| 文件 | 职责 |
|------|------|
| `tradingagents/dataflows/coingecko.py` | CoinGecko 加密货币数据（实时+历史） |
| `tradingagents/dataflows/fred_macro.py` | FRED 宏观经济指标（历史序列+快照） |
| `tradingagents/dataflows/sentiment_utils.py` | VADER 情绪评分（新闻+可选 Reddit） |
| `tradingagents/dataflows/local_cache.py` | Parquet 缓存读写（#3 直接调用） |

##### 配置方式（`default_config.py` / `main.py`）

```python
config["data_vendors"] = {
    "crypto_data": "coingecko",   # 无需 API Key
    "macro_data": "fred",         # 需 FRED_API_KEY（.env）
    "sentiment_data": "vader",    # 无需 API Key
}
```

##### 待补充内容（此实现未覆盖）
- **SEC EDGAR 财务报告采集**：10-K/10-Q 结构化解析（归属 #3，但采集接口可在此加）
- **数据采集脚本（批量历史预加载）**：供 #7 交付物使用，需单独编写
- **降级策略**：当 CoinGecko rate limit 触发时，自动降级到 yfinance 加密报价

##### 社媒评论时间过滤（2026-03-29 确认）

**核心要求**：社媒评论必须能按时间区分，确保回测时不使用未来数据。

| 数据源 | 时间字段 | 过滤机制 | 状态 |
|--------|---------|---------|------|
| yfinance 新闻 | `providerPublishTime`（Unix 时间戳） | 精确过滤到 `[date - lookback_days, date]` 窗口 | ✅ 已实现 |
| Reddit PRAW | `post.created_utc`（Unix 时间戳） | 精确过滤到同一窗口；`time_filter="month"` 仅用于扩大候选集 | ✅ 已修复（原为硬编码 `week`，`date` 参数未生效）|

**已修复 Bug（`sentiment_utils.py`）**：原 `get_reddit_sentiment()` 使用 `time_filter="week"` 硬编码，传入的 `date` 参数未被用于实际时间过滤。修复后改为 `time_filter="month"` 拉取更多候选，再通过 `post.created_utc` 按 `date` 参数精确筛选。

**已知限制**：yfinance `ticker.news` 只返回最近约 8 篇文章，不支持历史查询；历史回测日期较早时情绪数据可能为空，代码中已注释说明。Reddit 时间过滤已精确到日。

---

#### 数据流全链路梳理（2026-03-29）

##### 一、数据从采集到决策的完整路径

```
外部 API / 本地缓存
    │
    ▼
dataflows/ 采集层（coingecko.py / fred_macro.py / sentiment_utils.py / y_finance.py 等）
    │  返回格式化 CSV 字符串 + 写 Parquet 缓存
    ▼
interface.py route_to_vendor()  ← 统一路由入口，按 config["data_vendors"] 分配到对应 vendor
    │
    ▼
agents/utils/ 工具层（@tool 函数包装，LangChain Tool 格式）
    │  get_crypto_historical / get_news_sentiment / get_macro_snapshot 等
    ▼
agents/analysts/ 分析师节点（LangGraph 节点，调用 LLM + 工具）
    │  每个 Analyst 将分析报告写入 AgentState 对应字段
    │  market_analyst → state["market_report"]
    │  news_analyst   → state["news_report"]
    │  social_media_analyst / sentiment_analyst → state["sentiment_report"]
    │  fundamentals_analyst → state["fundamentals_report"]
    │  crypto_analyst → state["market_report"]
    │  macro_analyst  → state["news_report"]
    ▼
Bull/Bear Researcher（读取上述报告字段，生成多空辩论）
    │
    ▼
Research Manager（汇总辩论 → investment_plan）
    │
    ▼
Trader（读取 investment_plan + 报告 → trader_investment_plan）
    │
    ▼
Risk Debaters × 3（Aggressive / Conservative / Neutral，读取 trader_investment_plan）
    │
    ▼
Portfolio Manager（读取风险辩论结果 → 最终决策 BUY/HOLD/SELL）
    │
    ▼
SignalProcessor（提取单词决策标签）→ 输出
```

##### 二、各数据类型的具体用途

| 数据类型 | 采集函数 | 消费的 Analyst | 写入字段 | 传递给下游 |
|----------|---------|--------------|---------|-----------|
| 股票日K OHLCV | `get_stock_data` | market_analyst | `market_report` | Bull/Bear/Trader/Risk |
| 技术指标 | `get_indicators` | market_analyst | `market_report` | 同上 |
| 财务报表 | `get_fundamentals/balance_sheet/cashflow/income_statement` | fundamentals_analyst | `fundamentals_report` | 同上 |
| 新闻标题 | `get_news`, `get_global_news` | news_analyst | `news_report` | 同上 |
| 社媒情绪（VADER评分） | `get_news_sentiment`, `get_reddit_sentiment` | sentiment_analyst / social_media_analyst | `sentiment_report` | 同上 |
| 加密货币 OHLCV | `get_crypto_historical`, `get_crypto_price` | crypto_analyst | `market_report` | 同上 |
| 宏观经济指标 | `get_macro_snapshot`, `get_macro_indicator` | macro_analyst | `news_report` | 同上 |
| 历史决策记忆 | BM25 检索 `FinancialSituationMemory` | Bull/Bear Researcher | `investment_debate_state` | Research Manager |

##### 三、数据层潜在问题清单

**P1 — 高优先级（影响回测正确性）**

2. **CoinGecko 免费 API 限速严重**
   - 现状：公共端点无 API Key 时限速约 10-30 req/min，当 crypto analyst 连续调用多个工具时极易触发
   - 影响：工具调用失败或需等待 60 秒，整个 Agent 推理链中断
   - 状态：⚠️ **部分缓解** — `get_crypto_historical` 已优先走 yfinance（`BTC-USD`），CoinGecko 只用于实时快照；`_cg_get()` 已有 429 指数退避重试（等待 60s）。回测脚本建议跳过 `get_crypto_price` 实时快照工具调用，只用 `get_crypto_historical`

3. **FRED 数据发布存在滞后（Reporting Lag）**
   - 原状：宏观指标（如 CPI）通常滞后 2-6 周发布，`get_macro_snapshot` 和 `get_macro_indicator` 未区分"发布日"与"数据日"
   - 影响：回测中可能使用了当时尚未公开的数据（未来泄漏），在严格 Walk-forward 验证中违规
   - 状态：✅ **已修复（2026-03-29）** — `fred_macro.py` 所有 `fred.get_series()` 调用均加入 `realtime_start=date, realtime_end=date` 参数，FRED API 自动只返回该日期前已公开发布的数据，消除未来泄漏

5. **crypto_analyst 与 market_analyst 写入同一字段冲突**
   - 原状：两者都写 `state["market_report"]`，同时选中时后者覆盖前者
   - 状态：✅ **已修复（2026-03-29）** — `crypto_analyst` 改写 `state["crypto_report"]`；`AgentState` 新增 `crypto_report` 字段；所有下游节点同步更新，条件性读取并拼入 `curr_situation`

**P2 — 中优先级（影响数据完整性）**

6. **Parquet 缓存无版本控制**
   - 现状：缓存文件名为 `{start}_{end}.parquet`，若同一日期范围的数据被更新（如 yfinance 回填历史），旧缓存不会自动失效
   - 建议：写缓存时附加数据源版本或写入时间戳，提供 `--force-refresh` 标志

7. **加密货币 Ticker 映射表覆盖不全**
   - 现状：`CRYPTO_ID_MAP` 仅预置 15 个主流币，其余 ticker 通过 `upper().lower()` 猜测 CoinGecko ID，高概率失败
   - 建议：接入 CoinGecko `/coins/list` 动态构建映射，或给出明确错误提示

8. **macro_analyst 与 news_analyst 写入同一字段**
   - 同 P1-4/5 同类问题：macro_analyst 写 `state["news_report"]`，与 news_analyst 冲突
   - 建议：macro_analyst 写入 `state["macro_report"]`

**P3 — 低优先级（可接受的已知限制）**

9. **Reddit 仅能查询近 1 个月内的帖子**（PRAW `time_filter` 最长为 `year`，但实际可用历史有限）
10. **yfinance A股/港股数据存在缺口**（如停牌日、ST股退市等特殊情况未处理）
11. **技术指标需足够历史数据预热**（如 200-SMA 需要至少 200 天数据，若传入窗口不足会产生 NaN）


> **与 #3 的分工边界**：本任务只做数据接入与存储，不涉及向量化；宏观指标、情绪数据等同时被 #2（实时输入）和 #3（历史检索）使用，采集接口统一在此定义，#3 直接调用。


### 3. RAP 向量库外部数据（需支持回测的历史数据）

**职责**：负责向量化索引与检索逻辑，数据采集依赖 #2，不重复实现。

RAP 的核心是”按需检索”而非把所有数据塞进 prompt——当 agent 分析 NVDA 时，从向量库找出历史上最相似的市场条件下的决策记录，注入当前 prompt，让 LLM 有参照。

候选数据源（采集由 #2 负责，本任务负责向量化入库与检索）：

- **宏观经济指标**：利率、CPI、非农数据等时序数据 → 历史序列向量化，按相似市场条件检索
- **财务报告 / SEC 文件**：10-K、10-Q 等结构化财务数据，按 ticker + 时间索引入向量库（无实时需求，采集也归本任务）
- **分析师研报**：外部机构研报、评级变更，结构化后按相关性检索注入 prompt（无实时需求，采集也归本任务）
- **历史情绪数据**：社交媒体情绪历史记录，离线入库后按相似市场条件检索


## 我的设计工作

### 1. Agent 角色设计修改


**sentiment analyst功能改进**
| `get_reddit_sentiment` | Reddit API 只搜最近一个月帖子 | 实盘可用，回测不可用，无替代 |

**macro analyst改进**

**crypto链设计**
| `get_crypto_market_overview` | CoinGecko API 只返回当前排行，不接受日期参数 | 实盘可用，回测无替代 |

#### Agent 层集成（完整实现记录，2026-03-28）

除数据采集层外，同步完成了 Agent 层的完整接入，使新数据源可被 LangGraph 工作流中的 LLM 直接调用。

##### 新增工具文件（`tradingagents/agents/utils/`）

| 文件 | 包含 LangChain `@tool` | 说明 |
|------|------------------------|------|
| `crypto_tools.py` | `get_crypto_price`, `get_crypto_historical`, `get_crypto_market_overview` | 代理调用 `route_to_vendor()` → CoinGecko / yfinance |
| `macro_tools.py` | `get_macro_indicator`, `get_macro_snapshot`, `list_available_macro_series` | 代理调用 → FRED |
| `sentiment_tools.py` | `get_news_sentiment`, `get_reddit_sentiment` | 代理调用 → VADER |

##### 新增 Analyst Agent 文件（`tradingagents/agents/analysts/`）

| 文件 | 写入字段 | 绑定工具 |
|------|----------|----------|
| `crypto_analyst.py` | `state["crypto_report"]`（原为 `market_report`，已修复字段冲突） | `get_crypto_price`, `get_crypto_historical`, `get_crypto_market_overview`, `get_macro_snapshot` |
| `macro_analyst.py` | `state["news_report"]` | `get_macro_snapshot`, `get_macro_indicator`, `list_available_macro_series` |

##### 修改的现有文件

| 文件 | 变更内容 |
|------|--------|
| `tradingagents/dataflows/interface.py` | 新增 `crypto_data` / `macro_data` / `sentiment_data` VENDOR 类别；注册 8 个新函数的路由映射 |
| `tradingagents/default_config.py` | `data_vendors` 新增 `crypto_data: coingecko`, `macro_data: fred`, `sentiment_data: vader`；新增 `data_cache_enabled` / `data_cache_dir` |
| `.env.example` | 新增 `FRED_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `TRADEHIVE_CACHE_DIR` |
| `tradingagents/agents/utils/agent_utils.py` | 导入 9 个新工具（crypto / macro / sentiment tools） |
| `tradingagents/agents/__init__.py` | 导出 `create_crypto_analyst`, `create_sentiment_analyst`, `create_macro_analyst` |
| `tradingagents/graph/conditional_logic.py` | 新增 `should_continue_sentiment()`, `should_continue_crypto()`, `should_continue_macro()` |
| `tradingagents/graph/trading_graph.py` | 新增 `sentiment` / `crypto` / `macro` 三个 ToolNode；导入 9 个新工具 |
| `tradingagents/graph/setup.py` | `setup_graph()` 增加对 `"sentiment"`, `"crypto"`, `"macro"` 的节点注册与边连接 |
| `pyproject.toml` | 新增依赖：`fredapi>=0.5.1`, `vaderSentiment>=3.3.2`, `pyarrow>=14.0.0`, `praw>=7.7.0` |
| `main.py` | 新增注释形式的使用示例（加密货币分析 / 全量分析），原 NVDA 标准流程不变 |

##### selected_analysts 可用值（新旧对比）

```python
# 原有（保持不变）
["market", "social", "news", "fundamentals"]

# 新增（3 个）
["crypto", "sentiment", "macro"]

# 示例组合：加密货币分析
selected_analysts = ["crypto", "sentiment", "fundamentals"]

# 示例组合：全量分析（含宏观加分项）
selected_analysts = ["market", "social", "news", "fundamentals", "sentiment", "crypto", "macro"]
```

##### 依赖安装

```bash
pip install fredapi vaderSentiment pyarrow praw yfinance
```

> `yfinance` 为加密货币历史数据的主要来源（BTC-USD / ETH-USD），CoinGecko 仅用于实时快照。

### 2. Agent机制设计修改
#### Analyst Tool-Call 循环保护与异常传播

**现状分析**：

##### 当前
每个 Analyst 节点通过 LangGraph ReAct 循环调用工具：
```
Analyst Node (LLM 生成 tool_calls) → tools_xxx (ToolNode 执行) → Analyst Node → ... → Msg Clear
```
- 循环退出条件**仅**依赖 `len(result.tool_calls) == 0`，无最大迭代次数保护
- `ToolNode` 在工具抛异常时会捕获并包装为 `ToolMessage(content="Error: ...")` 返回给 LLM
- LLM 能看到错误信息并**智能调整参数**（如修正 ticker 格式），但对系统性错误（API key 缺失、服务宕机）无能为力，会无限重试

**各 Analyst 正常 tool_call 轮次统计**：

| Analyst | Tools 数量 | 正常轮次 | 说明 |
|---------|-----------|---------|------|
| Market | 2 | 2 | prompt 要求先 get_stock_data 再 get_indicators，串行 |
| Fundamentals | 4 | 1-2 | LLM 可能一次 batch 多个 tool_call |
| News | 2 | 1-2 | |
| Social | 1 | 1 | |
| Sentiment | 3 | 1-2 | |
| Crypto | 4 | 1-2 | |
| Macro | 3 | 2-3 | get_macro_indicator 可能被多次调用（拉不同 series） |

**风险场景**：

| 场景 | LLM 能否自愈 | 当前保护 |
|------|-------------|----------|
| 参数错误（ticker 格式不对） | ✅ 通常 1-2 次自纠正 | 无 |
| 部分工具失败（如 reddit API 未配置） | ✅ 放弃失败工具，用成功数据写报告 | 无 |
| 系统性失败（API key 无效、服务宕机、网络断） | ❌ 每次重试得到相同错误，无法自愈 | **无 → 死循环** |

**最严重的隐患 — 空报告静默穿透**：

当 Analyst 工具全部失败时，`report = ""`（空字符串）会一路传播：
```
Analyst (report="") → Bull/Bear Researcher (基于空数据辩论 → 纯幻觉)
    → Research Manager (基于幻觉辩论做决策) → Trader → Portfolio Manager
    → 输出格式完美但毫无数据基础的 BUY/SELL 决策
```
系统不会崩溃、不会报错，用户无法感知底层数据获取全部失败。


##### 改进方案：

**① Analyst 节点内部：tool_call 计数 + 截断后降级输出（合并原 ①②）**

核心问题：如果在 `conditional_logic.py` 的 conditional edge 处截断，LLM 最后一次输出的是带 `tool_calls` 的消息，
`report` 赋值逻辑只在 `tool_calls == 0` 时才执行 → **report 一定为空**，LLM 没有机会输出失败说明就被路由到下一个节点了。

因此，**计数和降级必须在 Analyst 节点内部完成**，而非在 conditional edge 中。改造方式：

```python
# 以 market_analyst.py 为例，其余 Analyst 同理
MAX_TOOL_ITERATIONS = 8

def market_analyst_node(state):
    # --- 计算当前节点已执行的 tool_call 轮次 ---
    tool_round_count = 0
    for m in reversed(state["messages"]):
        if hasattr(m, 'tool_calls') and m.tool_calls:
            tool_round_count += 1
        elif hasattr(m, 'type') and m.type == 'tool':
            continue  # ToolMessage，跳过
        else:
            break

    # --- 达到上限：不再绑定 tools，强制 LLM 用已有信息写报告 ---
    if tool_round_count >= MAX_TOOL_ITERATIONS:
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You have reached the maximum number of tool call attempts. "
             "Some or all data retrieval has failed. Based on whatever information "
             "IS available in the conversation history, write the best report you can. "
             "Clearly state which data sources were unavailable and mark your report "
             "with [PARTIAL DATA] or [DATA UNAVAILABLE] at the beginning."),
            MessagesPlaceholder(variable_name="messages"),
        ])
        result = (fallback_prompt | llm).invoke(state["messages"])
        # result.tool_calls 为空（因为没绑定 tools），一定走 report 赋值
        return {
            "messages": [result],
            "market_report": result.content,
        }

    # --- 正常路径（原逻辑不变）---
    # ... tools, prompt, chain 等原有代码 ...
    chain = prompt | llm.bind_tools(tools)
    result = chain.invoke(state["messages"])

    report = ""
    if len(result.tool_calls) == 0:
        report = result.content

    return {
        "messages": [result],
        "market_report": report,
    }
```

这样截断后 LLM 能：
- 看到之前所有 ToolMessage（包括成功和失败的）
- 基于已获取的部分数据写报告（graceful degradation）
- 明确标注哪些数据源缺失
- 输出不带 `tool_calls` 的纯文本 → `should_continue_xxx` 正常路由到 `Msg Clear` → report 不为空

**② Researcher/Manager 层：检测数据缺失并降级决策**

在 Bull/Bear Researcher 和 Research Manager 的 prompt 中加入数据缺失处理指令：

```
IMPORTANT: If any analyst report contains "[DATA UNAVAILABLE]" or "[PARTIAL DATA]", you MUST:
1. Explicitly acknowledge which data sources are missing in your analysis
2. Lower your conviction level accordingly
3. Do NOT fabricate data or make claims based on unavailable information
4. If critical data sources (market + fundamentals) are both unavailable, 
   recommend HOLD with a clear "INSUFFICIENT DATA" warning
```

**③ propagate() 最外层：返回值附带数据完整性标记**

```python
# trading_graph.py propagate() 返回前
UNAVAILABLE_MARKERS = ("[DATA UNAVAILABLE]", "[PARTIAL DATA]")

data_flags = {}
for field in ("market_report", "news_report", "fundamentals_report",
              "sentiment_report", "crypto_report"):
    val = final_state.get(field, "")
    data_flags[field] = (
        "available" if val.strip() and not any(m in val for m in UNAVAILABLE_MARKERS)
        else "partial" if val.strip()
        else "missing"
    )
# 附加到返回结果中，让调用方知道决策基于多完整的数据
```

**优先级**：① > ② > ③（先防死循环并保证降级输出，再做下游保护）




### 3. prompt优化
#### ✔ 重复注入修改
- 四份原始报告被所有后续 agent 无损重复注入（辩论每轮都重新拼入），无压缩无隔离：**辩论阶段报告重复注入优化**：当前辩手每轮调用都从 state 重新取四份完整报告拼入 prompt，报告内容不变却随轮次线性重复。改进思路：仅在辩论第一轮（`count == 0`）注入完整报告，后续轮次只追加辩论发言内容（`history`），减少冗余 token。默认1轮配置下影响有限，辩论轮数增大时收益显著。

#### prompt配套修改
目前的职能呢个：

Research Manager 的职能
从 research_manager.py:25-43 看，它就是牛熊辩论的裁判：

读取 Bull vs Bear 的完整辩论历史
决定站哪边（Buy / Sell / Hold）
给出一个投资计划传给 Trader
两个 Manager 的对比
Research Manager	Portfolio Manager
位置	牛熊辩论之后	风险辩论之后
裁决什么	Bull vs Bear → 要不要投	Aggressive vs Conservative vs Neutral → 怎么控风险
输出给谁	Trader	最终输出（END）
用的 LLM	deep_thinking_llm	deep_thinking_llm






看具体代码。以 Trader 为例（trader.py:18-19）：


curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
past_memories = memory.get_memories(curr_situation, n_matches=2)
四份报告被拼成一个字符串，传给 memory.get_memories() 做语义相似度匹配，找出过往类似市场状况下的经验教训。找到后，这些记忆（past_memory_str）才被放进 prompt。

但四份报告本身没有放进 Trader 的 prompt。 Trader 的 prompt 里只有：

investment_plan（Research Manager 的裁决）
past_memory_str（记忆系统返回的历史教训）
同理，Research Manager、Portfolio Manager 也是一样的模式——读报告只为查记忆，prompt 里不包含报告原文。

实际上谁真正读了报告原文
节点	报告放进 prompt 了吗
Bull/Bear Researcher	是，四份报告全文放进 prompt
Risk Debators (3个)	是，四份报告全文放进 prompt
Research Manager	否，只用于查记忆
Trader	否，只用于查记忆
Portfolio Manager	否，只用于查记忆
所以分析师报告只被辩论者直接使用。Research Manager、Trader、Portfolio Manager 这三个决策节点反而看不到报告原文，只能通过辩论历史间接获取信息。这其实是一个设计上可以改进的点——决策者本应该能直接看到一手数据。






trader可以基本维持目前的内容不变

风险辩论给出仓位规划，交易策略

portfolio职能：
综合裁决：Trader 说"在 88 块买入 NVDA，止损 82，目标 100"，但三个风险分析师对仓位有分歧（激进要 10%，保守要 2%，中立要 5%）——Portfolio Manager 拍板最终用多少仓位

冲突调解：如果 Trader 说 BUY 但保守派认为风险太大建议 HOLD，Portfolio Manager 做最终的 go/no-go 决定

输出结构化交易指令：把 Trader 的买卖点 + Risk Debators 的仓位规划，整合成回测系统能解析的标准 JSON 格式

### 4. 保证数据流结构化输出
#### 4.a 当前数据流（现状文档）

#### 4.b 约束策略

是按照目前的填槽位的方式更好，还是结构化输出更好



我的判断：哪些 非常有必要 加结构化输出
优先级 1（必须加）：

Portfolio Manager — 这是最终决策输出，直接决定交易信号。当前虽然 prompt 要求了 Rating / Executive Summary / Investment Thesis 三段结构，但完全靠 LLM 自觉。问题在于：

process_signal() 需要从中提取 Buy/Hold/Sell 信号，如果格式不对会解析失败
这是面向用户和下游回测的最终产物，格式不稳定直接影响可用性
应该用 structured output 强制返回：rating（枚举值）、executive_summary、investment_thesis、risk_levels、position_sizing 等字段
Trader — 仅要求结尾写 FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**，但 LLM 有时会写成别的格式（如 BUY 不加粗、漏掉前缀等）。应该至少强制提取出一个明确的 signal 枚举字段。

优先级 2（建议加）：

4 个 Analysts（Market / News / Social Media / Fundamentals）— 它们的报告会被后续所有 Agent 作为输入。如果格式混乱，后续 Agent 收到的上下文质量不稳定，影响整个链路。建议至少结构化为：summary（摘要）、key_findings（列表）、recommendation（倾向）、evidence_table（关键数据表）。

优先级 3（可以不加）：

Bull/Bear Researcher、3 个 Risk Debator、Research Manager — 这些是中间辩论环节，本质上就是自由文本讨论，格式化反而可能限制辩论的深度和灵活性。辩论内容不直接面向用户，而是作为上下文传给 Judge 和 Portfolio Manager，保持自由文本是合理的。


##### 三层保障策略

结构化输出只需三步即可保证，无需过度分级：

**第一层：虚拟工具（从输出来源限制）**
- 把期望的输出结构定义为虚拟 tool（tool calling），模型被引导以 tool call 形式返回结构化数据，格式可靠性远高于纯 prompt 指令
- 注意：虚拟工具 ≠ 约束解码。约束解码（constrained decoding）是在 token 采样层用 JSON Schema/正则硬约束生成，需 API 显式支持（如 OpenAI `response_format: json_schema`）或本地推理框架（Outlines、vLLM）。TradeHive 目前走 API 调用，使用的是虚拟工具而非约束解码
- LangChain `with_structured_output()` 底层即是 tool calling / JSON mode，可直接使用

**第二层：Pydantic 校验（检查格式 + 语义）**
- 为关键字段定义 Pydantic schema，校验字段类型、取值范围、业务语义
- 结合 `instructor` 库可实现：校验失败 → 将错误 feedback 回模型 → 自动重试
- 这层的价值不仅是格式检查，更是**语义约束**（如 action 只能是 buy/sell/hold，confidence 在 0-1 之间）

**第三层：兜底重试（仅守终点）**
- 仅针对 `final_trade_decision` 设置兜底验证节点（可建为 LangGraph 节点）
- 覆盖两类失败，策略不同：
  - **格式/校验失败**：将 ValidationError 信息 feedback 回模型重新生成
  - **调用失败**（网络超时、rate limit、5xx 等）：直接重试相同请求，指数退避，最多 3 次
- 其他中间节点无需兜底，前两层已足够

##### TradeHive 实施优先级

```
1. 关键决策节点接入 tool calling 约束输出
   优先节点：Research Manager → investment_plan
             Portfolio Manager → final_trade_decision

2. 定义 Pydantic schema，接入 instructor 或 with_structured_output()

3. final_trade_decision 加兜底节点（校验失败 feedback 重试 + 调用失败指数退避最多 3 次）
```

注意：报告类输出（分析师报告等）不宜过度约束格式，仅决策类输出需硬限制。


### 5. 对多 agent 策略结果进行金融回测与评估

**设计方案（Spec）：**

**评估指标：** CAGR = `(final/initial)^(252/n)-1`；夏普比率 = `(CAGR-0.05)/vol`；最大回撤 = `max(1-value/rolling_max)`；波动率 = `std(daily_returns)*sqrt(252)`

**对比基准：** Buy-and-Hold / 单 Agent Bot（无辩论）/ 传统量化策略（动量或RSI）

✅ 及格的鲁棒性
至少做到：

多时间段：
bull / bear / sideways
多资产：
不同股票 or ETF
多指标：
return
sharpe ratio
max drawdown

✅✅ 比较好的鲁棒性（推荐你做到这个）
再加：

train / test 分离（避免overfitting）
不同参数 sensitivity：
比如 risk threshold 改一下会不会崩
baseline 对比：
buy & hold
simple MA strategy

✅✅✅ 很强（能拿高分）
walk-forward testing（滚动窗口）
不同市场：
US vs crypto vs emerging
stress test：
极端行情（如 crash）
transaction cost / slippage


### 6. 长期记忆实现
#### 6.1 新增持久化记忆存储（Qdrant 方案）

**原始限制 → 改进方向**：
- ~~`FinancialSituationMemory` 只在内存中存储，进程重启后归零，无磁盘持久化~~ → **Qdrant 本地文件持久化，重启后自动加载**
- ~~BM25 是词频匹配，无法捕捉语义关联（如"利率攀升"和"加息周期"）~~ → **Qdrant 原生 Dense + Sparse 双路混合检索，RRF 融合**


Query改写：



**技术选型：Qdrant**

**Qdrant 核心优势**：

| 优势 | 说明 |
|------|------|
| **原生混合检索** | 同一 collection 内同时存储 Dense + Sparse 向量，内置 RRF（Reciprocal Rank Fusion）融合排序，一次 `query_points` 调用完成词汇匹配 + 语义匹配，无需外挂 BM25 库或手动融合逻辑 |
| **零部署本地持久化** | `QdrantClient(path="./qdrant_data")` 纯文件模式，无需 Docker、无需后台服务进程，`pip install` 即用，适合本项目的单机回测场景 |
| **检索阶段内过滤** | Payload filtering 在 HNSW 索引遍历时执行（pre-filtering），而非先召回再过滤（post-filtering）。按 ticker/日期范围筛选时不浪费召回名额，小数据集下尤为关键 |
| **原生 Sparse Vector** | 一等公民支持 `SparseVector` 类型，可直接存储 BM25 权重或 SPLADE 稀疏表示，与 Dense 向量共存于同一 point，无需维护两套索引 |
| **Python SDK 简洁** | API 设计一致，与本项目 Python + LangGraph 技术栈契合度高；相比 Weaviate 的 GraphQL 风格，集成代码量更少 |
| **量化压缩** | 支持 Scalar / Binary / Product Quantization，记忆量增长后可压缩向量降低内存占用，无需迁移存储引擎 |

**升级方案**：

记忆系统升级为 **Qdrant 混合检索 + 本地文件持久化**：
- **Dense 向量**：`all-MiniLM-L6-v2`（或 `bge-small-en`）编码语义，捕捉"利率攀升" ≈ "加息周期"等同义关联
- **Sparse 向量**：BM25/SPLADE 编码词汇特征，保留精确术语匹配能力（如 ticker 名、具体指标名）
- **RRF 融合**：Qdrant 内置 `Fusion.RRF`，一次 `query_points` 调用完成双路检索 + 排序融合
- **Payload 过滤**：存储 `ticker`、`trade_date`、`market_type` 等元数据，检索时可约束范围
- **持久化**：`QdrantClient(path="./qdrant_data")`，纯本地文件存储，进程重启后数据不丢失
- **冷启动保护**：保留 `memory_warmup_runs` 策略，积累到阈值后开放查询

**接口兼容**：`FinancialSituationMemory` 的 `add_situations()` / `get_memories()` 接口保持不变，底层替换为 Qdrant 实现，上层 agent 代码无需修改。

**Qdrant 混合检索调用示意**：
```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Prefetch, FusionQuery, Fusion,
    Filter, FieldCondition, MatchValue,
    SparseVector,
)

client = QdrantClient(path="./qdrant_data")

results = client.query_points(
    collection_name="financial_memory",
    prefetch=[
        Prefetch(query=dense_embedding, using="dense", limit=20),
        Prefetch(query=SparseVector(indices=sparse_ids, values=sparse_vals),
                 using="sparse", limit=20),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    query_filter=Filter(must=[
        FieldCondition(key="ticker", match=MatchValue(value="NVDA"))
    ]),
    limit=5,
)
```

cross-endcoder重排



#### 6.2 部分记忆机制重构
记忆功能冷启动策略，设置合理轮数不使用长期记忆，积累到一定阈值后开放查


版本	          训练期（12个月）	验证期（3个月）
Multi-agent 改进版	 积累记忆	    只读，跑验证
Single-agent 改进版  积累记忆	    只读，跑验证
Baseline（未改动）	 积累记忆	    只读，跑验证

### 有余力再做：滚动前向验证（Roll-forward Validation）

优化滚动窗口以降低过拟合，验证持久化记忆的泛化价值。

**设计方案（Spec）：**

**目标**：前向验证（Walk-forward Testing）避免未来数据泄漏（Look-ahead Bias），并评估 Agent 记忆积累在未见市场环境中的有效性。

**验证流程（训练窗口 = 12个月，验证窗口 = 3个月，步长 = 3个月）：**
训练期内 agent 是可读可写的——它在训练期的每个交易日做决策时，可以读取之前交易日积累的记忆，也可以写入新的记忆。
限制只在验证期：只读不写，防止验证期的经验反向影响评估。


| 窗口 | 训练窗口 (In-sample) | 验证窗口 (Out-of-sample) | 记忆状态 |
|---|---|---|---|
| W1 | 2022-10-01 ~ 2023-09-30 | 2023-10-01 ~ 2023-12-31 | 隔离，从空开始 |
| W2 | 2023-01-01 ~ 2023-12-31 | 2024-01-01 ~ 2024-03-31 | 隔离，从空开始 |
| W3 | 2023-04-01 ~ 2024-03-31 | 2024-04-01 ~ 2024-06-30 | 隔离，从空开始 |
| W4 | 2023-07-01 ~ 2024-06-30 | 2024-07-01 ~ 2024-09-30 | 隔离，从空开始 |
| W5 | 2023-10-01 ~ 2024-09-30 | 2024-10-01 ~ 2024-12-31 | 隔离，从空开始 |
| W6 | 2024-01-01 ~ 2024-12-31 | 2025-01-01 ~ 2025-03-31 | 隔离，从空开始 |

**记忆消融对照实验（Ablation）：**

每个验证窗口跑两个版本，验证记忆机制的真实价值：

| 版本 | 训练期 | 验证期 | 目的 |
|---|---|---|---|
| A：有记忆 | Agent 积累记忆 | 只读记忆 | 完整策略表现 |
| B：无记忆 | 跳过 | 空白记忆直接跑 | 基线对照 |

若版本 A 未能在多数窗口一致性地优于版本 B，说明记忆机制积累的是噪声而非泛化经验。

**防泄漏控制：**
- **数据源隔离**：yfinance / CoinGecko 按日期查询天然不泄漏；VADER 用 `lookback_days` 控制窗口；FRED 使用 `realtime_start` 参数
- **记忆窗口间隔离**：每个窗口使用独立的 memory store（按窗口 ID 分 namespace），跑完后归档，禁止跨窗口读取
- **验证期只读强制**：memory store 在验证期设置 `read_only=True` 开关，代码层面禁止写入，而非仅靠约定



### 有余力再做：6. 多资产组合设计

> **开发策略**：多资产组合作为**独立分支**（`feature/multi-asset-portfolio`）开发，不在 main 上直接改动。核心原则是**不改变图内部逻辑**——每个 ticker 独立走完整的单资产图，由图外部的调度层和 Portfolio 模块完成多资产聚合与仓位分配。
>
> **原因**：当前每个 Analyst 的 prompt 已包含大量单资产数据（行情、新闻、基本面），如果在图内部将多个 ticker 的信息拼接进 Analyst 上下文，token 数会线性增长，极易超出模型上下文窗口或严重降低分析质量。

#### 6.1 现状问题

当前系统是**单资产单次运行**：`propagate("NVDA", date)` 只分析一个标的，Portfolio Manager 输出决策时不知道组合中还有哪些资产、各自仓位多少、现金剩余多少。这导致：

- 无法做跨资产仓位分配（如"NVDA 已占 20%，BTC 不宜再加重"）
- 无法控制组合整体风险敞口（如"股票+加密总仓位不超过 80%"）
- 回测只能单资产独立跑，无法评估组合层面绩效

#### 6.2 设计目标

1. 每个决策周期内**逐个标的独立分析**，再由外部组合层**聚合为统一的组合交易计划**
2. 组合决策层能看到**当前持仓状态**（各资产仓位、现金、总市值）
3. **不改变图内部逻辑**——图仍然是单 ticker 输入、单 ticker 输出，Analyst/辩论/决策流程不变
4. 持仓系统**独立于图**，图只负责单资产分析和决策，不维护资金状态
5. 与现有回测设计（`回测逻辑设计.md`）兼容，升级为多资产版本

#### 6.3 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      回测循环 / 调度层                            │
│  for date in trading_dates:                                     │
│    portfolio_context = portfolio.get_summary()                   │
│    decisions = {}                                                │
│    for ticker in tickers:                                        │
│      decisions[ticker] = graph.propagate(ticker, date)  # 图不变 │
│    trade_plan = allocator.aggregate(decisions, portfolio_context) │
│    portfolio.execute_signals(trade_plan, date, prices)           │
└────────┬──────────────┬───────────────────┬─────────────────────┘
         │              │                   │
         ▼              ▼                   ▼
┌────────────────┐ ┌─────────────────┐ ┌──────────────────────────┐
│ TradingAgents  │ │ PortfolioAlloc  │ │ Portfolio (持仓模块)      │
│ Graph (不改动) │ │ (组合分配层)     │ │ (持仓 + 资金 + 交易记录)  │
│                │ │                 │ │                          │
│ 输入: ticker   │ │ 输入: 各ticker  │ │ - 维护现金和各资产持仓     │
│       date     │ │   的单资产决策   │ │ - 接收信号执行模拟交易     │
│ 输出: 单资产   │ │   + 持仓上下文   │ │ - 记录交易历史和每日快照   │
│   交易决策     │ │ 输出: 组合交易   │ │ - 计算绩效指标            │
│                │ │   计划           │ │                          │
└────────────────┘ └─────────────────┘ └──────────────────────────┘
```

**关键原则**：

- **图不变**：`TradingAgentsGraph` 保持单 ticker 输入输出，内部 State、Analyst、辩论逻辑完全不动
- **外层循环**：调度层逐 ticker 调用图，收集各自的单资产决策
- **组合分配层**（`PortfolioAllocator`）：汇总所有单资产决策 + 当前持仓上下文，产出组合级交易计划
- **单向依赖**：图不感知持仓系统，持仓系统只接收组合分配层的输出

#### 6.4 图外组合分配层

图内部不做任何改造。多资产的聚合和仓位分配由**图外部的 `PortfolioAllocator`** 完成：

```
调度层逐 ticker 调用图（图内部逻辑不变）
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  各 ticker 的单资产决策（图的原始输出）                │
│  { "NVDA": {action: "BUY", confidence: 0.8, ...},   │
│    "BTC":  {action: "HOLD", confidence: 0.5, ...},   │
│    "AAPL": {action: "SELL", confidence: 0.7, ...} }  │
└──────────────────────┬──────────────────────────────┘
                       │ + portfolio_context（当前持仓摘要）
                       ▼
┌─────────────────────────────────────────────────────┐
│  PortfolioAllocator（组合分配层，图外部独立模块）      │
│                                                     │
│  职责：                                              │
│  - 综合各 ticker 的单资产决策和置信度                  │
│  - 结合当前持仓状态，做跨资产仓位分配                  │
│  - 控制组合整体风险敞口                               │
│  - 输出结构化的组合交易计划                            │
└──────────────────────┬──────────────────────────────┘
                       ▼
              组合交易计划（见 6.7）
```

**实现方式**：`PortfolioAllocator` 可以是基于规则的（按 confidence 加权分配），也可以用 LLM 做组合级决策（将所有单资产决策摘要 + 持仓上下文作为 prompt），但这都发生在图外部，不影响图的运行。

#### 6.5 Portfolio 持仓模块

**文件位置**：`tradingagents/portfolio/`，与 `graph/` 平级。

```
tradingagents/
├── portfolio/
│   ├── __init__.py
│   ├── models.py          # Position, Trade, Snapshot 数据结构
│   ├── portfolio.py       # Portfolio 核心类
│   └── signal_mapper.py   # 信号 → 目标仓位比例的翻译规则
```

**数据结构**：

```python
@dataclass
class Position:
    ticker: str
    quantity: float            # 持有数量
    avg_cost: float            # 平均成本价
    current_price: float       # 当前市价
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity

@dataclass
class Trade:
    ticker: str
    date: str
    action: str                # BUY / SELL
    quantity: float
    price: float
    commission: float
    signal: str                # 原始信号
    reason: str                # 决策摘要（可选）

@dataclass
class Snapshot:
    date: str
    cash: float
    positions: Dict[str, Position]
    total_equity: float        # cash + sum(market_value)
```

**Portfolio 核心接口**：

```python
class Portfolio:
    def __init__(self, initial_cash: float = 100_000, commission_rate: float = 0.001):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.snapshots: List[Snapshot] = []

    # ── 供调度层调用 ──

    def get_summary(self) -> str:
        """生成持仓摘要文本，注入图的 portfolio_context 字段"""
        # 输出示例：
        # Portfolio Status:
        #   Cash: $45,000 (45.0%)
        #   NVDA: 100 shares @ $850 = $85,000 (42.5%) | avg_cost: $780 | PnL: +$7,000
        #   BTC-USD: 0.5 units @ $65,000 = $32,500 (16.3%) | avg_cost: $60,000 | PnL: +$2,500
        #   Total Equity: $200,000
        #   Available for new positions: $45,000

    def execute_signals(self, trade_plan: dict, date: str, prices: Dict[str, float]):
        """接收组合交易计划，逐个 ticker 执行"""
        # trade_plan 结构见 6.7

    def update_prices(self, prices: Dict[str, float], date: str):
        """每日更新市价，记录快照"""

    def get_returns(self, ticker: str = None) -> float:
        """单资产或组合整体收益"""

    def get_performance_metrics(self) -> Dict:
        """CAGR、夏普、最大回撤、波动率"""
```

#### 6.7 组合级结构化输出

`PortfolioAllocator` 汇总各 ticker 的单资产决策后，输出**组合交易计划**：

```json
{
  "date": "2024-05-10",
  "portfolio_rating": "RISK_ON",
  "total_target_invested_pct": 0.75,
  "cash_reserve_pct": 0.25,
  "positions": [
    {
      "ticker": "NVDA",
      "rating": "BUY",
      "target_position_pct": 0.30,
      "entry_plan": [
        {"phase": "A", "action": "BUY", "allocation_pct": 1.0, "trigger": "IMMEDIATE", "limit_price": null}
      ],
      "stop_loss": 780.00,
      "take_profit": 950.00,
      "time_horizon_days": 30
    },
    {
      "ticker": "BTC-USD",
      "rating": "OVERWEIGHT",
      "target_position_pct": 0.20,
      "entry_plan": [
        {"phase": "A", "action": "BUY", "allocation_pct": 0.5, "trigger": "IMMEDIATE", "limit_price": null},
        {"phase": "B", "action": "BUY", "allocation_pct": 0.5, "trigger": "PRICE_BELOW", "limit_price": 62000}
      ],
      "stop_loss": 58000,
      "take_profit": 75000,
      "time_horizon_days": 14
    },
    {
      "ticker": "AAPL",
      "rating": "HOLD",
      "target_position_pct": 0.25,
      "entry_plan": [],
      "stop_loss": null,
      "take_profit": null,
      "time_horizon_days": null
    }
  ]
}
```

**约束**：`sum(target_position_pct) + cash_reserve_pct = 1.0`，由校验层检查，超出则按比例缩放。

#### 6.8 回测循环升级

从单资产循环升级为组合循环。**图的调用方式不变**（仍然是 `propagate(ticker, date)`），多资产通过外层循环实现：

```python
from tradingagents.portfolio.portfolio import Portfolio
from tradingagents.portfolio.allocator import PortfolioAllocator

portfolio = Portfolio(initial_cash=100_000)
allocator = PortfolioAllocator()
tickers = ["NVDA", "BTC-USD", "AAPL"]

for date in trading_dates:
    # 1. 获取当前持仓上下文
    portfolio_context = portfolio.get_summary()

    # 2. 逐 ticker 独立调用图（图内部逻辑不变）
    decisions = {}
    for ticker in tickers:
        decision, _ = ta.propagate(ticker, date)  # 原有接口，不改动
        decisions[ticker] = decision

    # 3. 组合分配层：汇总单资产决策 + 持仓上下文 → 组合交易计划
    trade_plan = allocator.aggregate(decisions, portfolio_context)

    # 4. 获取当日价格
    prices = {t: get_price(t, date) for t in tickers}

    # 5. 执行组合交易计划
    portfolio.execute_signals(trade_plan, date, prices)

    # 6. 更新价格 + 记录快照
    portfolio.update_prices(prices, date)

    # 7. 反思
    ta.reflect_and_remember(portfolio.get_returns())

# 绩效评估
metrics = portfolio.get_performance_metrics()
portfolio.export_history("eval_results/portfolio_backtest/")
```

#### 6.9 与现有回测设计的兼容

现有 `回测逻辑设计.md` 的**两阶段解耦思路**保留：

- **阶段1**（昂贵）：逐 ticker 批量生成单资产决策，保存为 JSON（每个决策日包含各 ticker 的独立决策 + 组合分配层产出的组合交易计划）
- **阶段2**（廉价）：读取组合交易计划 + 行情，模拟多资产交易，计算组合绩效

区别在于：
- 阶段1 每个决策日先逐 ticker 跑图（图不变），再由 `PortfolioAllocator` 聚合为组合交易计划
- 阶段2 的 Simulator 从单资产模拟升级为多资产 Portfolio 模拟
- 绩效指标增加组合层面维度（资产权重变化、跨资产相关性等）

#### 6.10 实现优先级

> **注意**：全部在 `feature/multi-asset-portfolio` 分支上开发，图内部代码不做任何改动。

| 步骤 | 内容 | 依赖 |
|------|------|------|
| ① | `portfolio/models.py` — Position, Trade, Snapshot 数据结构定义 | 无 |
| ② | `portfolio/portfolio.py` — 核心持仓管理 + 信号执行 | ① |
| ③ | `portfolio/signal_mapper.py` — 单资产决策到仓位比例的映射规则 | ② |
| ④ | `portfolio/allocator.py` — PortfolioAllocator 组合分配层 | ①③ |
| ⑤ | 回测循环升级：外层多 ticker 循环 + 组合分配 + Portfolio 模拟 | ②④ |
| ⑥ | 绩效评估升级：组合层面指标 | ⑤ |

先做 ①②③④（全部是图外部新模块，不动现有代码），再做 ⑤⑥（回测集成）。


# TradeHive - 开发者文档

> **版本**: v0.2.2
> **生成日期**: 2026-03-23
> **项目名称**: TradingAgents (TradeHive)
> **定位**: 基于多智能体 LLM 的金融交易决策框架

---

## 1. 项目概述

TradeHive 是一个模拟真实交易公司组织架构的多智能体系统。系统通过部署多个具有专业分工的 LLM 智能体，协作完成市场数据收集、分析辩论、风险评估，最终输出交易决策信号。

**核心技术栈**:
- **编排引擎**: LangGraph (状态图工作流)
- **LLM 集成**: LangChain (OpenAI / Anthropic / Google / xAI / OpenRouter / Ollama)
- **数据源**: yfinance (默认) / Alpha Vantage (备选)
- **记忆系统**: BM25 词汇相似度匹配 (rank-bm25)
- **CLI**: Typer + Rich + Questionary

---

## 2. 系统架构

### 2.1 分层架构图

```
┌──────────────────────────────────────────────────────┐
│                    CLI 层 (cli/)                       │
│        用户交互 · 参数配置 · 实时状态展示               │
├──────────────────────────────────────────────────────┤
│                  图编排层 (graph/)                      │
│     LangGraph StateGraph · 条件路由 · 状态传播          │
├──────────────────────────────────────────────────────┤
│                  智能体层 (agents/)                     │
│   分析师 · 研究员 · 交易员 · 风控辩论员 · 管理者        │
├──────────────────────────────────────────────────────┤
│                  工具层 (agents/utils/)                 │
│    股票数据 · 技术指标 · 基本面 · 新闻 · 记忆系统       │
├──────────────────────────────────────────────────────┤
│                 数据流层 (dataflows/)                   │
│     接口路由 · yfinance · Alpha Vantage · stockstats   │
├──────────────────────────────────────────────────────┤
│                LLM 客户端层 (llm_clients/)              │
│   OpenAI · Anthropic · Google · xAI · OpenRouter       │
└──────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
TradeHive/
├── main.py                          # 程序化调用入口示例
├── test.py                          # 数据获取测试
├── pyproject.toml                   # 包元数据与依赖
├── .env.example                     # 环境变量模板
│
├── cli/                             # CLI 交互层
│   ├── main.py                      # Typer 应用主入口 (含 MessageBuffer)
│   ├── utils.py                     # 输入辅助 (ticker/日期/分析师/模型选择)
│   ├── models.py                    # 数据模型 (AnalystType 枚举)
│   ├── config.py                    # CLI 配置 (公告 URL 等)
│   ├── stats_handler.py             # LangChain 回调统计处理器
│   ├── announcements.py             # 公告展示 (从 api.tauric.ai 获取)
│   └── static/welcome.txt           # 欢迎界面 ASCII Art
│
├── tradingagents/                   # 核心框架
│   ├── __init__.py                  # 设置 PYTHONUTF8=1 环境变量
│   ├── default_config.py            # 默认配置字典
│   │
│   ├── graph/                       # 图编排引擎
│   │   ├── trading_graph.py         # 主编排器 TradingAgentsGraph
│   │   ├── setup.py                 # GraphSetup - 图构建
│   │   ├── conditional_logic.py     # 条件路由逻辑
│   │   ├── propagation.py           # 状态初始化/传播
│   │   ├── reflection.py            # 决策反思与学习
│   │   └── signal_processing.py     # 输出信号提取
│   │
│   ├── agents/                      # 智能体定义
│   │   ├── __init__.py              # 统一导出所有 create_* 工厂函数
│   │   ├── analysts/                # 分析师 (数据收集)
│   │   │   ├── market_analyst.py    # 市场/技术分析
│   │   │   ├── social_media_analyst.py  # 社交媒体情感分析
│   │   │   ├── news_analyst.py      # 全球宏观新闻分析
│   │   │   └── fundamentals_analyst.py  # 基本面分析
│   │   │
│   │   ├── researchers/             # 研究员 (辩论)
│   │   │   ├── bull_researcher.py   # 看多研究员
│   │   │   └── bear_researcher.py   # 看空研究员
│   │   │
│   │   ├── trader/                  # 交易员
│   │   │   └── trader.py            # 生成投资计划
│   │   │
│   │   ├── risk_mgmt/              # 风险管理辩论
│   │   │   ├── aggressive_debator.py    # 激进派
│   │   │   ├── conservative_debator.py  # 保守派
│   │   │   └── neutral_debator.py       # 中立派
│   │   │
│   │   ├── managers/               # 管理者 (决策者)
│   │   │   ├── research_manager.py  # 研究经理 (裁判 Bull/Bear)
│   │   │   └── portfolio_manager.py # 投资组合经理 (最终决策)
│   │   │
│   │   └── utils/                  # 工具与辅助
│   │       ├── agent_states.py     # 状态定义 (AgentState 等)
│   │       ├── agent_utils.py      # 工具导入汇总 + build_instrument_context + create_msg_delete
│   │       ├── core_stock_tools.py # 股票数据工具
│   │       ├── technical_indicators_tools.py  # 技术指标工具
│   │       ├── fundamental_data_tools.py      # 基本面数据工具
│   │       ├── news_data_tools.py             # 新闻数据工具
│   │       └── memory.py           # BM25 记忆系统
│   │
│   ├── dataflows/                  # 数据访问层
│   │   ├── interface.py            # 统一路由接口 (route_to_vendor)
│   │   ├── config.py               # 数据源配置管理 (get_config/set_config)
│   │   ├── y_finance.py            # yfinance 实现
│   │   ├── yfinance_news.py        # yfinance 新闻
│   │   ├── alpha_vantage.py        # Alpha Vantage 入口
│   │   ├── alpha_vantage_common.py # AV 公共工具 + AlphaVantageRateLimitError
│   │   ├── alpha_vantage_stock.py  # AV 股票数据
│   │   ├── alpha_vantage_indicator.py  # AV 技术指标
│   │   ├── alpha_vantage_fundamentals.py  # AV 基本面
│   │   ├── alpha_vantage_news.py   # AV 新闻
│   │   ├── stockstats_utils.py     # 技术指标计算 (stockstats)
│   │   └── utils.py                # 数据工具函数
│   │
│   └── llm_clients/                # LLM 客户端抽象
│       ├── base_client.py          # 抽象基类 BaseLLMClient + normalize_content()
│       ├── factory.py              # 工厂函数 create_llm_client()
│       ├── openai_client.py        # OpenAI/xAI/OpenRouter/Ollama + NormalizedChatOpenAI
│       ├── anthropic_client.py     # Claude 系列 + NormalizedChatAnthropic
│       ├── google_client.py        # Gemini 系列 + NormalizedChatGoogleGenerativeAI
│       └── validators.py           # 模型名称验证
│
└── tests/
    └── test_ticker_symbol_handling.py  # Ticker 符号处理测试
```

---

## 3. 核心工作流

### 3.1 完整执行流程

> **重要**: 分析师阶段为**串行执行** (按 `selected_analysts` 列表顺序依次执行)，而非并行。
> 每个分析师完成后，其消息会被清除 (`create_msg_delete`) 再传递给下一个分析师。

```
用户输入 (Ticker + 日期)
        │
        ▼
┌──────────────────────────────────────────────────┐
│            第一阶段: 数据分析 (串行)               │
│                                                  │
│  市场分析师 ──► [工具调用循环] ──► 消息清除         │
│       │                                          │
│       ▼                                          │
│  社交媒体分析师 ──► [工具调用循环] ──► 消息清除     │
│       │                                          │
│       ▼                                          │
│  新闻分析师 ──► [工具调用循环] ──► 消息清除         │
│       │                                          │
│       ▼                                          │
│  基本面分析师 ──► [工具调用循环] ──► 消息清除       │
│       │                                          │
│       ▼                                          │
│  各分析师报告写入 AgentState 对应字段               │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│          第二阶段: 投资研究辩论                     │
│                                                  │
│  ┌────────────┐   ┌────────────┐                │
│  │ 看多研究员  │◄─►│ 看空研究员  │                │
│  │ (Bull)      │   │ (Bear)     │                │
│  └──────┬──────┘   └──────┬─────┘                │
│         └────────┬────────┘                      │
│    (循环 count < 2 * max_debate_rounds)           │
│                  ▼                               │
│  ┌──────────────────────────────┐                │
│  │ 研究经理 (Research Manager)   │                │
│  │ → 裁决: BUY / HOLD / SELL    │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│            第三阶段: 交易计划                      │
│                                                  │
│  ┌──────────────────────────────┐                │
│  │ 交易员 (Trader)               │                │
│  │ → 生成具体投资计划            │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│          第四阶段: 风险管理辩论                     │
│                                                  │
│  激进派 ──► 保守派 ──► 中立派 ──► (循环)          │
│  (循环 count < 3 * max_risk_discuss_rounds)       │
│                  ▼                               │
│  ┌──────────────────────────────┐                │
│  │ 投资组合经理 (Portfolio Mgr)  │                │
│  │ → 最终决策 (五级评级)         │                │
│  └──────────────┬───────────────┘                │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────────────┐
│              信号处理与输出                        │
│                                                  │
│   BUY │ OVERWEIGHT │ HOLD │ UNDERWEIGHT │ SELL   │
└──────────────────────────────────────────────────┘
```

### 3.2 辩论机制

系统包含两轮结构化辩论:

**投资辩论 (Bull vs Bear)**:
1. 看多研究员基于分析报告 + 历史记忆，提出看多论点
2. 看空研究员基于分析报告 + 历史记忆，提出看空论点
3. 双方轮流辩论，终止条件: `count >= 2 * max_debate_rounds` (每人发言一次计 count+1)
4. 研究经理 (Deep Thinking LLM) 综合评估，做出 BUY/HOLD/SELL 裁决

**风险辩论 (Aggressive vs Conservative vs Neutral)**:
1. 三方分别从不同风险偏好角度评估交易计划
2. 轮流发言顺序: Aggressive → Conservative → Neutral → 循环
3. 终止条件: `count >= 3 * max_risk_discuss_rounds` (三人各发言一次计 count+3)
4. 投资组合经理 (Deep Thinking LLM) 综合评估，输出五级评级

### 3.3 消息清除机制

每个分析师完成后, `create_msg_delete()` 会:
1. 删除 messages 列表中所有消息 (通过 `RemoveMessage`)
2. 添加一条 `HumanMessage(content="Continue")` 占位消息 (Anthropic 兼容性要求)

这确保下一个分析师从干净的消息历史开始, 只通过 AgentState 的报告字段传递数据。

---

## 4. 状态管理

### 4.1 AgentState (主状态)

```python
class AgentState(MessagesState):
    """继承自 LangGraph 的 MessagesState (自带 messages 字段)"""
    company_of_interest: Annotated[str, "Company that we are interested in trading"]
    trade_date: Annotated[str, "What date we are trading at"]

    sender: Annotated[str, "Agent that sent this message"]

    # 分析师报告
    market_report: Annotated[str, "Report from the Market Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Media Analyst"]
    news_report: Annotated[str, "Report from the News Researcher"]
    fundamentals_report: Annotated[str, "Report from the Fundamentals Researcher"]

    # 投资决策链
    investment_debate_state: Annotated[InvestDebateState, "..."]
    investment_plan: Annotated[str, "Plan generated by the Analyst"]
    trader_investment_plan: Annotated[str, "Plan generated by the Trader"]

    # 风险管理链
    risk_debate_state: Annotated[RiskDebateState, "..."]
    final_trade_decision: Annotated[str, "Final decision made by the Risk Analysts"]
```

> **注意**: `AgentState` 继承 `MessagesState` (非 `TypedDict`), 其 `messages` 字段自带 `operator.add` 归约器, 支持消息追加和 `RemoveMessage` 操作。

### 4.2 InvestDebateState (投资辩论状态)

```python
class InvestDebateState(TypedDict):
    bull_history: Annotated[str, "Bullish Conversation history"]    # 字符串拼接, 非列表
    bear_history: Annotated[str, "Bearish Conversation history"]    # 字符串拼接, 非列表
    history: Annotated[str, "Conversation history"]                 # 合并辩论全文
    current_response: Annotated[str, "Latest response"]             # 最新论点 (含 "Bull/Bear Analyst:" 前缀)
    judge_decision: Annotated[str, "Final judge decision"]          # 研究经理裁决
    count: Annotated[int, "Length of the current conversation"]     # 发言计数器
```

### 4.3 RiskDebateState (风控辩论状态)

```python
class RiskDebateState(TypedDict):
    aggressive_history: Annotated[str, "Aggressive Agent's Conversation history"]
    conservative_history: Annotated[str, "Conservative Agent's Conversation history"]
    neutral_history: Annotated[str, "Neutral Agent's Conversation history"]
    history: Annotated[str, "Conversation history"]               # 合并辩论全文
    latest_speaker: Annotated[str, "Analyst that spoke last"]     # 用于路由 (Aggressive/Conservative/Neutral/Judge)
    current_aggressive_response: Annotated[str, "Latest response by the aggressive analyst"]
    current_conservative_response: Annotated[str, "Latest response by the conservative analyst"]
    current_neutral_response: Annotated[str, "Latest response by the neutral analyst"]
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]   # 发言计数器
```

> **注意**: 所有 `*_history` 和 `history` 字段类型均为 `str` (字符串拼接), **不是** `list`。辩论历史通过字符串 `+=` 不断追加。

---

## 5. 智能体详细设计

### 5.1 智能体一览

| 智能体 | 文件 | LLM 类型 | ToolNode 绑定的工具 | 记忆实例 |
|--------|------|----------|-------------------|---------|
| 市场分析师 | `analysts/market_analyst.py` | Quick | `get_stock_data`, `get_indicators` | 无 |
| 社交媒体分析师 | `analysts/social_media_analyst.py` | Quick | `get_news` | 无 |
| 新闻分析师 | `analysts/news_analyst.py` | Quick | `get_news`, `get_global_news` (⚠️ `get_insider_transactions` 存在于 ToolNode 但未通过 `bind_tools` 绑定给 LLM，实际不可调用) | 无 |
| 基本面分析师 | `analysts/fundamentals_analyst.py` | Quick | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` | 无 |
| 看多研究员 | `researchers/bull_researcher.py` | Quick | 无 | `bull_memory` |
| 看空研究员 | `researchers/bear_researcher.py` | Quick | 无 | `bear_memory` |
| 研究经理 | `managers/research_manager.py` | **Deep** | 无 | `invest_judge_memory` |
| 交易员 | `trader/trader.py` | Quick | 无 | `trader_memory` |
| 激进派辩论员 | `risk_mgmt/aggressive_debator.py` | Quick | 无 | 无 |
| 保守派辩论员 | `risk_mgmt/conservative_debator.py` | Quick | 无 | 无 |
| 中立派辩论员 | `risk_mgmt/neutral_debator.py` | Quick | 无 | 无 |
| 投资组合经理 | `managers/portfolio_manager.py` | **Deep** | 无 | `portfolio_manager_memory` |

### 5.2 双模型策略

- **Deep Thinking LLM** (如 gpt-5.2, claude-opus-4-6): 用于需要深度推理的决策节点 → 研究经理、投资组合经理
- **Quick Thinking LLM** (如 gpt-5-mini, claude-sonnet-4-6): 用于数据处理和论点生成 → 分析师、研究员、辩论员、交易员、信号处理器、反思器

### 5.3 智能体创建模式

所有智能体采用**闭包工厂模式**: `create_xxx()` 返回一个闭包节点函数, 供 LangGraph 直接作为节点使用。

**分析师模式** (有工具):
```python
def create_market_analyst(llm):
    def market_analyst_node(state):
        tools = [get_stock_data, get_indicators]
        # 1. 从 state 提取 trade_date, company_of_interest
        # 2. 构建 ChatPromptTemplate + system_message
        # 3. chain = prompt | llm.bind_tools(tools)
        # 4. result = chain.invoke(state["messages"])
        # 5. 如果没有 tool_calls, 将 result.content 写入 market_report
        return {"messages": [result], "market_report": report}
    return market_analyst_node
```

**研究员/辩论员模式** (无工具, 有辩论状态):
```python
def create_bull_researcher(llm, memory):
    def bull_node(state):
        # 1. 从 state 提取四份分析报告 + 辩论历史
        # 2. 从 memory.get_memories() 检索相似情景
        # 3. 构建 prompt 字符串 (含报告 + 历史 + 记忆)
        # 4. response = llm.invoke(prompt)
        # 5. 更新 investment_debate_state (追加历史, count+1)
        return {"investment_debate_state": new_state}
    return bull_node
```

**交易员模式** (使用 functools.partial):
```python
def create_trader(llm, memory):
    def trader_node(state, name):
        # ... 生成投资计划 ...
        return {"messages": [result], "trader_investment_plan": result.content, "sender": name}
    return functools.partial(trader_node, name="Trader")
```

### 5.4 Ticker 上下文注入

`build_instrument_context(ticker)` 为每个智能体生成标准化的 Ticker 说明:

```python
def build_instrument_context(ticker: str) -> str:
    return (
        f"The instrument to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )
```

此函数在所有 4 个分析师 (市场、社交媒体、新闻、基本面) 以及研究经理、交易员、投资组合经理中被调用, 确保国际 Ticker 后缀不被丢失。

---

## 6. 数据流层

### 6.1 工具总览

系统共有 **9 个 `@tool` 工具**，全部定义在 `agents/utils/` 下，仅在第一阶段（分析师数据收集）被调用。后续的辩论、裁判、交易决策阶段均不使用工具。

| 工具 | 定义文件 | 参数 | 功能 | 绑定给 |
|------|---------|------|------|--------|
| `get_stock_data` | `core_stock_tools.py` | `symbol`, `start_date`, `end_date` | 获取 OHLCV 历史股价数据 | 市场分析师 |
| `get_indicators` | `technical_indicators_tools.py` | `symbol`, `indicator`, `curr_date`, `look_back_days=30` | 获取技术指标（支持逗号分隔多个指标名） | 市场分析师 |
| `get_news` | `news_data_tools.py` | `ticker`, `start_date`, `end_date` | 获取个股相关新闻 | 社交媒体分析师、新闻分析师 |
| `get_global_news` | `news_data_tools.py` | `curr_date`, `look_back_days=7`, `limit=5` | 获取全球宏观新闻 | 新闻分析师 |
| `get_insider_transactions` | `news_data_tools.py` | `ticker` | 获取内部人交易记录 | ⚠️ 存在于新闻 ToolNode 但未 bind_tools 给 LLM |
| `get_fundamentals` | `fundamental_data_tools.py` | `ticker`, `curr_date` | 获取公司基本面概览 | 基本面分析师 |
| `get_balance_sheet` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取资产负债表 | 基本面分析师 |
| `get_cashflow` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取现金流量表 | 基本面分析师 |
| `get_income_statement` | `fundamental_data_tools.py` | `ticker`, `freq="quarterly"`, `curr_date=None` | 获取利润表 | 基本面分析师 |

**工具调用时机**：分析师节点调用 LLM → LLM 返回 `tool_calls` → ToolNode 执行工具并返回结果 → LLM 继续分析或停止。当 LLM 不再返回 `tool_calls` 时，该分析师阶段结束，进入 Msg Clear → 下一阶段。工具调用轮次无硬性限制，依赖 LLM 自主判断，仅靠全局 `recursion_limit=100` 兜底。

### 6.2 数据源路由机制

```
Tool 调用 (如 get_stock_data)
        │
        ▼
  route_to_vendor(method, *args, **kwargs)
        │
        ├─ get_category_for_method(method) → 确定所属分类
        ├─ get_vendor(category, method)
        │   ├─ 优先检查 tool_vendors[method] (工具级覆盖)
        │   └─ 回退到 data_vendors[category] (分类级配置)
        │
        ▼
  构建降级链: [配置的主供应商, ...其余可用供应商]
        │
        ├─ 尝试第一个供应商
        │   ├─ 成功 → 返回数据
        │   └─ AlphaVantageRateLimitError → 继续
        │
        ├─ 尝试第二个供应商
        │   └─ ...
        │
        └─ 全部失败 → RuntimeError
```

> **关键细节**: 供应商配置值支持逗号分隔 (如 `"yfinance,alpha_vantage"`), `route_to_vendor` 会按顺序拆分为主供应商列表。**只有 `AlphaVantageRateLimitError` 才会触发降级**, 其他异常会直接抛出。

### 6.2 数据分类映射

| 分类 | 默认供应商 | 包含工具 |
|------|-----------|---------|
| `core_stock_apis` | yfinance | `get_stock_data` |
| `technical_indicators` | yfinance | `get_indicators` |
| `fundamental_data` | yfinance | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` |
| `news_data` | yfinance | `get_news`, `get_global_news`, `get_insider_transactions` |

### 6.3 技术指标

市场分析师通过 prompt 从以下指标中选择最多 8 个互补指标:

| 类别 | 指标 | 说明 |
|------|------|------|
| 移动均线 | `close_50_sma` | 50 周期简单移动均线 |
| | `close_200_sma` | 200 周期简单移动均线 |
| | `close_10_ema` | 10 周期指数移动均线 |
| MACD | `macd`, `macds`, `macdh` | MACD线 / 信号线 / 柱状图 |
| 动量 | `rsi` | 相对强弱指标 (70/30 阈值) |
| 波动率 | `boll`, `boll_ub`, `boll_lb` | 布林带 (中/上/下轨, 20周期 2σ) |
| | `atr` | 平均真实波幅 |
| 成交量 | `vwma` | 成交量加权移动均线 |

底层通过 stockstats 库计算, 数据源为 yfinance 或 Alpha Vantage 的 OHLCV 数据。

---

## 7. LLM 客户端抽象层

### 7.1 类层次

```
normalize_content(response)          # 独立函数: 将列表类型的 content 标准化为字符串
                                     # 提取 type="text" 的块, 丢弃 reasoning/metadata

BaseLLMClient (ABC)
├── get_llm() → Any                  # 抽象方法: 返回配置好的 LangChain LLM 实例
├── validate_model() → bool          # 抽象方法: 验证模型名是否合法
│
├── OpenAIClient
│   ├── 内部使用 NormalizedChatOpenAI (继承 ChatOpenAI, invoke 时自动 normalize)
│   ├── 支持: openai, xai, openrouter, ollama
│   ├── 原生 OpenAI: 启用 use_responses_api=True (Responses API)
│   ├── 第三方 (xai/openrouter/ollama): 使用标准 Chat Completions
│   ├── 可透传参数: timeout, max_retries, reasoning_effort, api_key, callbacks, http_client, http_async_client
│   └── 供应商自动配置: xai→api.x.ai, openrouter→openrouter.ai, ollama→localhost:11434
│
├── AnthropicClient
│   ├── 内部使用 NormalizedChatAnthropic (继承 ChatAnthropic, invoke 时自动 normalize)
│   ├── 可透传参数: timeout, max_retries, api_key, max_tokens, callbacks, http_client, http_async_client, effort
│   └── effort 参数控制扩展思维 (low/medium/high)
│
└── GoogleClient
    ├── 内部使用 NormalizedChatGoogleGenerativeAI
    ├── 可透传参数: timeout, max_retries, google_api_key, callbacks, http_client, http_async_client
    └── 思维配置按模型系列区分:
        ├── Gemini 3 系列: thinking_level (minimal/low/medium/high)
        │   └── Gemini 3 Pro 不支持 "minimal", 自动映射为 "low"
        └── Gemini 2.5 系列: thinking_budget (-1=动态, 0=禁用)
```

### 7.2 工厂函数

```python
create_llm_client(provider, model, base_url=None, **kwargs) → BaseLLMClient
# provider: "openai" | "anthropic" | "google" | "xai" | "openrouter" | "ollama"
#
# 路由逻辑:
#   openai / ollama / openrouter → OpenAIClient
#   xai                          → OpenAIClient (provider="xai")
#   anthropic                    → AnthropicClient
#   google                       → GoogleClient
```

### 7.3 内容标准化机制

多个 LLM 供应商 (OpenAI Responses API, Gemini 3, Claude Extended Thinking) 返回的 `response.content` 为类型化块列表:
```python
[{"type": "reasoning", "text": "..."}, {"type": "text", "text": "实际内容"}]
```

每个客户端使用 `Normalized*` 包装类, 在 `invoke()` 后自动调用 `normalize_content()` 将其转为纯字符串, 确保下游所有智能体都收到一致的字符串格式。

---

## 8. 记忆系统

### 8.1 FinancialSituationMemory

```python
class FinancialSituationMemory:
    """混合检索金融情景记忆（BM25 + 稠密向量），持久化到本地 ChromaDB"""

    def __init__(self, name: str, persist_dir: str = "./memory_store", config: dict = None):
        # name: 记忆实例标识符，同时作为 ChromaDB collection 名称
        # persist_dir: 磁盘持久化目录，默认 ./memory_store
        # config: 保留用于 API 兼容性

    def add_situations(self, situations_and_advice: List[Tuple[str, str]]):
        # 添加 (情景描述, 推荐/反思) 对
        # 同时写入: BM25 内存索引 + ChromaDB 向量库（自动持久化到磁盘）

    def get_memories(self, current_situation: str, n_matches: int = 1) -> List[dict]:
        # 混合检索: BM25 召回 + 稠密向量召回，通过 RRF 融合排序后返回 top-n
        # 返回: [{"matched_situation": str, "recommendation": str, "similarity_score": float}]

    def clear(self):
        # 清空内存索引 + ChromaDB collection

    def _load_from_disk(self):
        # 启动时从 ChromaDB 恢复 BM25 内存索引，实现重启持久化
```

**特点**:
- **混合检索**: BM25（词汇精确匹配）+ 稠密向量（语义相似匹配），RRF 融合排序
- **磁盘持久化**: ChromaDB 自动落盘，进程重启后记忆不丢失，启动时自动加载
- 离线可用（embedding 使用本地模型，无需 API 调用）
- 每个关键角色独立 collection，互不干扰
- BM25 分词: 小写化 + 按 `\b\w+\b` 正则拆分；向量化: sentence-transformers 本地模型

### 8.2 记忆使用者

| 代码中的实例名 | 使用智能体 | 用途 | 检索数 |
|---------------|-----------|------|--------|
| `bull_memory` | 看多研究员 | 检索历史看多反思 | 2 |
| `bear_memory` | 看空研究员 | 检索历史看空反思 | 2 |
| `trader_memory` | 交易员 | 检索历史交易反思 | 2 |
| `invest_judge_memory` | 研究经理 | 检索历史投资判断反思 | 2 |
| `portfolio_manager_memory` | 投资组合经理 | 检索历史组合决策反思 | 2 |

### 8.3 反思学习循环

```
执行交易决策 → 获取实际收益/损失 (数值)
        │
        ▼
  reflect_and_remember(returns_losses)
        │
        ├─ Reflector 使用 quick_thinking_llm (非 deep)
        ├─ 对 5 个角色分别生成反思:
        │   ├─ Bull Researcher  → 反思看多论点 vs 实际结果
        │   ├─ Bear Researcher  → 反思看空论点 vs 实际结果
        │   ├─ Trader           → 反思交易计划 vs 实际结果
        │   ├─ Invest Judge     → 反思投资裁决 vs 实际结果
        │   └─ Portfolio Manager → 反思最终决策 vs 实际结果
        │
        ├─ 输入上下文 = 四份分析报告拼接
        ├─ Reflection Prompt 要求分析: 推理/改进/总结/精简查询
        └─ 反思结果存入对应记忆 → 下次 get_memories() 时可检索到
```

---

## 9. 图编排引擎

### 9.1 TradingAgentsGraph (主入口)

```python
class TradingAgentsGraph:
    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,    # 默认使用 DEFAULT_CONFIG
        callbacks: Optional[List] = None,  # LangChain 回调处理器 (如 StatsCallbackHandler)
    ):
        # 1. set_config(config) → 更新 dataflows 全局配置
        # 2. 创建 data_cache 目录
        # 3. 根据 provider 提取 thinking kwargs (reasoning_effort / effort / thinking_level)
        # 4. create_llm_client() × 2 (deep + quick)
        # 5. 初始化 5 个 FinancialSituationMemory 实例
        # 6. 创建 4 个 ToolNode (market/social/news/fundamentals)
        # 7. 初始化 ConditionalLogic, GraphSetup, Propagator, Reflector, SignalProcessor
        # 8. graph_setup.setup_graph(selected_analysts) → 编译图

    def propagate(self, company_name, trade_date):
        # debug=True: graph.stream() 逐步打印
        # debug=False: graph.invoke() 一次执行
        # 日志写入 eval_results/{ticker}/TradingAgentsStrategy_logs/
        # 返回 (final_state, signal)

    def reflect_and_remember(self, returns_losses):
        # 对当前 state 进行 5 角色反思

    def process_signal(self, full_signal):
        # SignalProcessor 提取评级
```

### 9.2 图节点与边 (精确流程)

```mermaid
flowchart TD
    START([START])

    %% ===== 第一阶段：分析师串行 =====
    START --> MA["① Market Analyst<br/>(quick_think_llm)"]
    MA -->|有 tool_calls| TM["tools_market<br/>• get_stock_data<br/>• get_indicators"]
    TM --> MA
    MA -->|"无 tool_calls → 写入 market_report"| MC1["Msg Clear Market"]

    MC1 --> SA["② Social Media Analyst<br/>(quick_think_llm)"]
    SA -->|有 tool_calls| TS["tools_social<br/>• get_news"]
    TS --> SA
    SA -->|"无 tool_calls → 写入 sentiment_report"| MC2["Msg Clear Social"]

    MC2 --> NA["③ News Analyst<br/>(quick_think_llm)"]
    NA -->|有 tool_calls| TN["tools_news<br/>• get_news<br/>• get_global_news<br/>• get_insider_transactions"]
    TN --> NA
    NA -->|"无 tool_calls → 写入 news_report"| MC3["Msg Clear News"]

    MC3 --> FA["④ Fundamentals Analyst<br/>(quick_think_llm)"]
    FA -->|有 tool_calls| TF["tools_fundamentals<br/>• get_fundamentals<br/>• get_balance_sheet<br/>• get_cashflow<br/>• get_income_statement"]
    TF --> FA
    FA -->|"无 tool_calls → 写入 fundamentals_report"| MC4["Msg Clear Fundamentals"]

    %% ===== 第二阶段：投资辩论（无工具） =====
    MC4 --> Bull["Bull Researcher<br/>(quick_think_llm + bull_memory)"]

    Bull -->|"count < 2 × max_debate_rounds"| Bear["Bear Researcher<br/>(quick_think_llm + bear_memory)"]
    Bull -->|"count ≥ 2 × max_debate_rounds"| RM["Research Manager<br/>(deep_think_llm + invest_judge_memory)"]

    Bear -->|"count < 2 × max_debate_rounds"| Bull
    Bear -->|"count ≥ 2 × max_debate_rounds"| RM

    %% ===== 第三阶段：交易计划（无工具） =====
    RM -->|"输出 investment_plan"| Trader["Trader<br/>(quick_think_llm + trader_memory)"]

    %% ===== 第四阶段：风控辩论（无工具） =====
    Trader -->|"输出 trader_investment_plan"| Agg["Aggressive Analyst<br/>(quick_think_llm)"]

    Agg -->|"count < 3 × max_risk_discuss_rounds"| Con["Conservative Analyst<br/>(quick_think_llm)"]
    Agg -->|"count ≥ 3 × max_risk_discuss_rounds"| PM["Portfolio Manager<br/>(deep_think_llm + pm_memory)"]

    Con -->|"count < 3 × max_risk_discuss_rounds"| Neu["Neutral Analyst<br/>(quick_think_llm)"]
    Con -->|"count ≥ 3 × max_risk_discuss_rounds"| PM

    Neu -->|"count < 3 × max_risk_discuss_rounds"| Agg
    Neu -->|"count ≥ 3 × max_risk_discuss_rounds"| PM

    %% ===== 输出 =====
    PM -->|"输出 final_trade_decision"| END([END])
```

> **注**:
> - 分析师数量和顺序由 `selected_analysts` 列表决定，默认为 `["market", "social", "news", "fundamentals"]`。
> - **仅第一阶段（分析师）使用工具**，后续阶段全部是纯 LLM 文本交互。
> - 投资辩论和风控辩论中，**每个节点**都独立调用同一个条件路由函数判断是否终止。
> - `Msg Clear` 使用 `RemoveMessage` 删除所有 messages，仅保留 `HumanMessage("Continue")`，防止多分析师消息叠加撑爆上下文。

### 9.3 条件路由逻辑详细

**分析师工具路由** (`should_continue_{type}`):
- 检查 `messages[-1].tool_calls` 是否存在
- 有工具调用 → `"tools_{type}"` (执行工具后返回分析师继续)
- 无工具调用 → `"Msg Clear {Type}"` (清除消息, 进入下一阶段)

**投资辩论路由** (`should_continue_debate`, 同时应用于 Bull Researcher 和 Bear Researcher 两个节点):
- `count >= 2 * max_debate_rounds` → `"Research Manager"` (结束辩论)
- `current_response` 以 `"Bull"` 开头 → `"Bear Researcher"` (轮到看空方)
- 否则 → `"Bull Researcher"` (轮到看多方)

**风控辩论路由** (`should_continue_risk_analysis`, 同时应用于 Aggressive、Conservative、Neutral 三个节点):
- `count >= 3 * max_risk_discuss_rounds` → `"Portfolio Manager"` (结束辩论)
- `latest_speaker` 以 `"Aggressive"` 开头 → `"Conservative Analyst"`
- `latest_speaker` 以 `"Conservative"` 开头 → `"Neutral Analyst"`
- 否则 → `"Aggressive Analyst"`

---

## 10. 配置系统

### 10.1 默认配置 (default_config.py)

```python
DEFAULT_CONFIG = {
    # 路径
    "project_dir": "<tradingagents 包的绝对路径>",
    "data_cache_dir": "<project_dir>/dataflows/data_cache",

    # LLM 设置
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",

    # 供应商特定思维配置
    "openai_reasoning_effort": None,     # "low" | "medium" | "high"
    "anthropic_effort": None,            # "low" | "medium" | "high"
    "google_thinking_level": None,       # "minimal" | "low" | "medium" | "high"

    # 辩论轮次
    "max_debate_rounds": 1,              # 投资辩论轮数 (实际发言 = 2 * N)
    "max_risk_discuss_rounds": 1,        # 风控辩论轮数 (实际发言 = 3 * N)
    "max_recur_limit": 100,              # ⚠️ 此配置项当前未生效：Propagator() 初始化时未读取此值，递归限制硬编码为 100

    # 数据源 (分类级)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # 可选: alpha_vantage, yfinance
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },

    # 数据源 (工具级覆盖, 优先级更高)
    "tool_vendors": {},
}
```

### 10.2 环境变量 (.env.example)

```bash
# LLM 供应商 (设置你使用的那个)
OPENAI_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=
XAI_API_KEY=
OPENROUTER_API_KEY=

# 数据源 (可选, 使用 Alpha Vantage 时需要)
ALPHAVANTAGE_API_KEY=
```

### 10.3 配置传递流程

```
TradingAgentsGraph.__init__(config)
    │
    ├─ set_config(config)  → 写入 dataflows.config 全局变量
    │                        所有 route_to_vendor() 调用通过 get_config() 读取
    │
    ├─ _get_provider_kwargs()  → 根据 provider 提取 thinking 配置
    │   ├─ google → {"thinking_level": ...}
    │   ├─ openai → {"reasoning_effort": ...}
    │   └─ anthropic → {"effort": ...}
    │
    └─ create_llm_client(provider, model, base_url, **kwargs)
        └─ 传入 LangChain LLM 构造函数
```

---

## 11. CLI 交互流程

### 11.1 用户交互步骤

```
1. 输入 Ticker 代号 (支持国际后缀: .TO, .L, .HK, .T)
   → ⚠️ normalize_ticker_symbol() (strip + upper) 定义于 cli/utils.py，但实际 CLI 流程中
     main.py 的本地 get_ticker() 函数 shadow 了它，使用 typer.prompt 且未调用归一化
2. 选择分析日期 (YYYY-MM-DD, 含格式校验 + 拒绝未来日期)
3. 选择启用的分析师 (多选 checkbox: Market/Social/News/Fundamentals)
4. 选择研究深度:
   - Shallow (1轮) / Medium (3轮) / Deep (5轮)
   → 同时设置 max_debate_rounds 和 max_risk_discuss_rounds
5. 选择 LLM 供应商 (OpenAI/Google/Anthropic/xAI/Openrouter/Ollama)
   → 返回 (display_name, base_url) 元组
6. 选择 Quick Thinking 模型 + Deep Thinking 模型 (选项随供应商变化，合并为一步)
7. [供应商特定] 思维配置 (仅在对应供应商时出现):
   - OpenAI → 选择 Reasoning Effort (Medium/High/Low)
   - Anthropic → 选择 Effort Level (High/Medium/Low)
   - Google → 选择 Thinking Mode (Enable/Minimal)
8. 执行分析 (实时展示进度)
```

### 11.2 MessageBuffer (实时状态追踪)

`MessageBuffer` 是 CLI 层的核心状态管理类:

- **agent_status**: 动态追踪每个智能体的 `pending` / `in_progress` / `completed` / `error` 状态
- **report_sections**: 追踪 7 个报告段 (4 分析报告 + investment_plan + trader_plan + final_decision)
- **messages/tool_calls**: 带时间戳的消息和工具调用记录 (deque, 最大 100 条)
- **init_for_analysis(selected_analysts)**: 根据选定分析师动态构建状态和报告追踪
- **get_completed_reports_count()**: 统计已完成报告数 (要求报告有内容 + 对应智能体已 completed)

固定团队 (始终包含):
- Research Team: Bull Researcher, Bear Researcher, Research Manager
- Trading Team: Trader
- Risk Management: Aggressive Analyst, Neutral Analyst, Conservative Analyst
- Portfolio Management: Portfolio Manager

### 11.3 StatsCallbackHandler (统计回调)

线程安全的 LangChain 回调处理器, 追踪:
- `llm_calls`: LLM 调用次数 (on_llm_start + on_chat_model_start)
- `tool_calls`: 工具调用次数 (on_tool_start)
- `tokens_in`: 输入 Token 数 (从 AIMessage.usage_metadata 提取)
- `tokens_out`: 输出 Token 数

### 11.4 公告系统

CLI 启动时从 `https://api.tauric.ai/v1/announcements` 获取公告 (超时 1 秒), 失败时显示 GitHub 链接回退文本。

---

## 12. 输出格式

### 12.1 最终决策信号

五级评级:

| 信号 | 含义 |
|------|------|
| **BUY** | 强烈建议买入 |
| **OVERWEIGHT** | 建议增持 |
| **HOLD** | 建议持有/观望 |
| **UNDERWEIGHT** | 建议减持 |
| **SELL** | 强烈建议卖出 |

信号由 `SignalProcessor` 使用 quick_thinking_llm 从 Portfolio Manager 的完整决策文本中提取。

### 12.2 输出内容

`propagate()` 返回 `(state, signal)`:
- `state`: 完整 AgentState dict, 包含所有分析报告和辩论记录
- `signal`: 字符串, 由 LLM 从 `final_trade_decision` 中提取的评级

### 12.3 日志存储

每次执行自动生成 JSON 日志:
- 路径: `eval_results/{ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json`
- 内容: 所有报告、辩论历史、裁决、最终决策的完整快照

---

## 13. 设计模式

| 模式 | 应用 |
|------|------|
| **工厂模式** | `create_llm_client()`, `create_*_analyst()`, `create_*_researcher()`, `create_trader()` |
| **闭包模式** | 所有智能体节点函数通过闭包捕获 llm/memory |
| **策略模式** | 数据供应商路由 (yfinance ↔ Alpha Vantage) |
| **装饰器模式** | LangChain `@tool` 工具注册; `Normalized*` 包装类 |
| **状态模式** | AgentState + InvestDebateState + RiskDebateState 管理工作流 |
| **备选链 (Fallback)** | 数据供应商失败时自动降级 (仅限速率限制错误) |
| **全局配置** | `get_config()` / `set_config()` 管理数据源配置 |
| **部分应用** | Trader 使用 `functools.partial` 绑定 name 参数 |

---

## 14. 依赖清单

| 类别 | 库 | 用途 |
|------|-----|------|
| LLM 编排 | `langgraph` (>=0.4.8), `langchain-core` (>=0.3.81) | 图工作流引擎 |
| LLM 客户端 | `langchain-openai` (>=0.3.23), `langchain-anthropic` (>=0.3.15), `langchain-google-genai` (>=2.1.5) | 多供应商支持 |
| LLM 扩展 | `langchain-experimental` (>=0.3.4) | 实验性功能 |
| 数据获取 | `yfinance` (>=0.2.63) | 股票/新闻数据 |
| 技术分析 | `pandas` (>=2.3.0), `stockstats` (>=0.6.5) | 指标计算 |
| 回测 | `backtrader` (>=1.9.78) | 回测框架 |
| 记忆 | `rank-bm25` (>=0.2.2) | BM25 相似度匹配 |
| CLI | `typer` (>=0.21.0), `questionary` (>=2.1.0), `rich` (>=14.0.0) | 终端交互 |
| 网络/解析 | `requests` (>=2.32.4), `parsel` (>=1.10.0) | HTTP 请求 / HTML 解析 |
| 数据存储 | `redis` (>=6.2.0) | ⚠️ 在 pyproject.toml 中存在，但当前代码中无任何使用，用途待确认 |
| 工具 | `python-dotenv`, `pytz` (>=2025.2), `tqdm` (>=4.67.1), `typing-extensions` (>=4.14.0) | 环境/时区/进度条 |

> Python 版本要求: `>=3.10`

---

## 15. 扩展点

1. **新增分析师**: 在 `agents/analysts/` 添加新文件, 在 `agents/__init__.py` 导出, 在 `graph/setup.py` 注册节点和边, 在 `conditional_logic.py` 添加 `should_continue_xxx` 方法
2. **新增数据源**: 在 `dataflows/` 实现供应商模块, 在 `interface.py` 的 `VENDOR_METHODS` 和 `VENDOR_LIST` 中注册
3. **新增 LLM 供应商**: 继承 `BaseLLMClient`, 实现 `get_llm()` 和 `validate_model()`, 在 `factory.py` 注册路由, 在 `validators.py` 添加模型白名单
4. **调整辩论轮次**: 修改配置中 `max_debate_rounds` / `max_risk_discuss_rounds` (注意: 实际发言次数分别为 2N 和 3N)
5. **自定义评级体系**: 修改 `signal_processing.py` 的 system prompt 中的评级选项
6. **新增记忆角色**: 在 `TradingAgentsGraph.__init__` 中创建新的 `FinancialSituationMemory` 实例, 在 `Reflector` 中添加对应反思方法
