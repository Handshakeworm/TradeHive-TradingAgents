分析师步骤其实偏向：编排式工作流

当前的multi-agent的设计是decentralized

在各个环节注意中间件设计，确保大模型按需求做事不跑偏不幻觉输出结构正确

全程注意推理三明治
### 对比基准

多 agent bot 必须与以下基准进行对比：

- **Buy-and-Hold**：基准指数或 ETF，或者买入持有股票
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

### RAP 向量库外部数据（需支持回测的历史数据）

**职责**：负责向量化索引与检索逻辑，数据采集依赖 #2，不重复实现。

RAP 的核心是”按需检索”而非把所有数据塞进 prompt——当 agent 分析 NVDA 时，从向量库找出历史上最相似的市场条件下的决策记录，注入当前 prompt，让 LLM 有参照。

候选数据源（采集由 #2 负责，本任务负责向量化入库与检索）：

- **宏观经济指标**：利率、CPI、非农数据等时序数据 → 历史序列向量化，按相似市场条件检索
- **财务报告 / SEC 文件**：10-K、10-Q 等结构化财务数据，按 ticker + 时间索引入向量库（无实时需求，采集也归本任务）
- **分析师研报**：外部机构研报、评级变更，结构化后按相关性检索注入 prompt（无实时需求，采集也归本任务）
- **历史情绪数据**：社交媒体情绪历史记录，离线入库后按相似市场条件检索


## 我的设计工作

### 1. Agent 角色设计修改


### 2. crypto链的制作以及优化


### 3. prompt优化


### 4. 保证数据流结构化输出
#### 4.a 当前数据流（现状文档）



### 5. 对多 agent 策略结果进行金融回测与评估

回测区间为 2025-2-14 to 2025-8-14
记忆功能关闭

**对比基准：** Buy-and-Hold / 单 Agent Bot（无辩论）/ 传统量化策略（动量或RSI）



在baseline的情况下，如果每天操作，在前两个月直接-33%的亏损，跑输了Buy and hold NVDA的-18%
采用每5天一决策，情况大大改善




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
- **数据源隔离**：yfinance 按日期查询天然不泄漏；VADER 用 `lookback_days` 控制窗口
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
