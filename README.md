### 此项目为基于tauric reasearch开源的TradingAgents: Multi-Agents LLM Financial Trading Framework的multi-agent项目改编

## 以下为简要介绍，此后作者会完善详细的对原系统的升级内容，如您感兴趣可以浏览'项目介绍.md'

我们的项目实现了原先项目基础上，200%至500%的收益提升

在测试下，我们拥有最好的回撤控制，最高的收入
（仓位大小偏好可以自由设置，图中最高仓位，大概就在75%）

![alt text](image.png)

![alt text](image-1.png)

![alt text](image-2.png)

## 原项目其实并不属于可用状态，需要大幅改进，以下是我们做的修改：

新增了agent角色，并使得分析师节点并行

修改了数据源，使项目支持回测功能，新增数据缓存机制

修改了分析师节点后所有节点的角色定位，使其分工更加清晰

支持仓位管理，并可以自由调整风险偏好


## 更多机制优势

使用残差连接，允许关键信息在跨日时间序列中传播

使用状态机，将ticker的状态分为7个regime

```
confirmed_uptrend   → topping
early_uptrend       → confirmed_uptrend / consolidation
consolidation       → early_uptrend / early_downtrend
topping             → consolidation / early_downtrend/ early_uptrend
early_downtrend     → confirmed_downtrend / consolidation
confirmed_downtrend → bottoming
bottoming           → consolidation / early_uptrend / early_downtrend
```

（状态机和残差连接在满足特定需求的同时，也降低了系统敏感度）

推理顺序修改，需要的kv cache先被生成

硬编码关键操作：仓位管理

| Regime | 仓位区间 | 意图 |
|--------|---------|------|
| confirmed_uptrend | **75-100%** | 强势趋势，重仓 |
| early_uptrend | 30-60% | 趋势确认中，试探 |
| consolidation | 0-15% | 震荡期，观望为主 |
| topping | 20-40% | 顶部区域，减仓 |
| early_downtrend | 0-10% | 趋势恶化，撤退 |
| **confirmed_downtrend** | **0% 硬锁** | 完全空仓 |
| bottoming | 5-20% | 底部试探建仓 |

硬编码关键操作：确认主升/下行趋势，退出主升/下行趋势。我们使用组合指标，命中多个阈值的机制才识别主升和主跌，在此设计下状态机中的confirmed_uptrend和confirmed_downtrend难以进入，也难以退出


支持结构化输出和重试，因此具有更多功能和拓展可能


**如想快速了解原项目设计，也可以浏览DEV_SPEC_original文档**

如想参阅原项目，请移步至此查阅：https://github.com/TauricResearch/TradingAgents
