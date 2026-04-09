# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[TradingAgents 多智能体交易系统架构 - 中国期货市场版本]
- Date: 2026-04-09
- Context: 用户要求将项目从股票市场重构为中国期货市场，使用 akshare 作为数据源
- Category: 代码结构
- Instructions:
  - 这是一个基于 LangGraph 的多智能体自动交易和分析系统
  - 模拟真实交易公司的运作方式
  - 数据流：输入 futures symbol + date → Analyst Team → Researcher Team (辩论) → Trader → Risk Management Team (辩论) → Final Decision
  - 数据源: akshare (中国期货市场)

  智能体架构 (Graph):
  - Analyst Team (4类): Market Analyst, Social Analyst, News Analyst, Fundamentals Analyst
  - Researcher Team: Bull Researcher ↔ Bear Researcher (辩论) → Research Manager 裁决
  - Trader Agent: 根据分析师报告生成交易计划
  - Risk Management Team (3类): Aggressive ↔ Conservative ↔ Neutral (三角辩论) → Portfolio Manager 裁决
  - 最终输出评级: BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL

  核心组件文件:
  - tradingagents/graph/trading_graph.py: 主编排器 TradingAgentsGraph
  - tradingagents/graph/setup.py: GraphSetup 构建 LangGraph
  - tradingagents/graph/propagation.py: Propagator 初始化状态
  - tradingagents/graph/conditional_logic.py: ConditionalLogic 控制流转
  - tradingagents/graph/signal_processing.py: SignalProcessor 处理最终信号
  - tradingagents/graph/reflection.py: Reflector 反思与记忆
  - tradingagents/agents/utils/memory.py: FinancialSituationMemory 基于 BM25 的记忆检索

  数据层文件:
  - tradingagents/dataflows/akshare_futures.py: akshare 期货数据获取实现
  - tradingagents/dataflows/interface.py: 数据路由接口
  - tradingagents/dataflows/config.py: 配置管理
  - tradingagents/agents/utils/agent_utils.py: 工具函数封装
  - tradingagents/agents/utils/core_stock_tools.py: get_main_contract, get_futures_ohlc
  - tradingagents/agents/utils/technical_indicators_tools.py: get_futures_indicators
  - tradingagents/agents/utils/fundamental_data_tools.py: get_futures_basis, get_futures_inventory, get_futures_position
  - tradingagents/agents/utils/news_data_tools.py: get_futures_news, get_global_futures_news

  已删除的文件:
  - tradingagents/dataflows/y_finance.py
  - tradingagents/dataflows/yfinance_news.py
  - tradingagents/dataflows/alpha_vantage*.py
  - tradingagents/dataflows/stockstats_utils.py

  适用市场:
  - 中国期货市场: 大连商品交易所(DCE)、郑州商品交易所(CZCE)、上海期货交易所(SHFE)、中国金融期货交易所(CFFEX)
  - 示例品种: 螺纹钢(rb)、热轧卷板(hc)、铁矿石(i)、焦煤(jm)、焦炭(j)、原油(sc)、黄金(au)、白银(ag)、铜(cu)、铝(al)等
