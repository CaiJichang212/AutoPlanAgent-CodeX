# Autoplan Agent

基于 LangChain/LangGraph 的自主规划数据分析与异常检测智能体系统。提供 FastAPI 服务与 CLI 命令行工具，支持从任务理解、计划生成、交互式确认到动态执行与多格式报告（Markdown/HTML/PDF）生成的全流程自动化。

## 🌟 核心功能

- **任务深度理解**：利用 LLM 解析用户需求，输出结构化的任务理解报告（目标、范围、约束、交付物）。
- **动态规划引擎**：结合预设模板与数据库 Schema，自动生成包含 SQL 查询、清洗、分析、可视化的多步骤执行计划。
- **交互式循环**：支持用户对计划进行反馈修改，触发再规划（Re-planning），确保分析方向准确。
- **强力执行工具箱**：
  - **MySQL 增强**：支持复杂查询、SQL 安全卫士与执行计划（EXPLAIN）分析。
  - **数据处理**：内置清洗（Cleaning）、探索性分析（EDA）、统计检验（Stats）。
  - **智能挖掘**：集成异常检测（Anomaly Detection）、趋势分析等算法。
  - **多维可视化**：支持 Plotly 与 Matplotlib 渲染。
- **自动化报告**：汇总执行产物，基于 Jinja2 模板生成专业分析报告。
- **高可靠性**：利用 LangGraph Checkpoint 实现任务中断恢复与状态持久化。

## 📂 项目结构

```text
.
├── api/                # FastAPI 服务入口及路由定义
│   └── routers/        # 业务路由 (health, runs)
├── autoplan_agent/     # 核心逻辑框架
│   ├── llm/            # LLM 适配、Jinja2 提示词模板与运行时
│   ├── schemas/        # Pydantic 统一数据模型 (Plan, Artifacts等)
│   ├── storage/        # 运行数据持久化 (RunStore) 与 LangGraph Checkpoint
│   ├── tools/          # 内置工具箱（MySQL, DF处理, 统计, 可视化, 报告, 智能挖掘）
│   ├── config.py       # 全局配置 (Pydantic Settings)
│   ├── executor.py     # 计划执行引擎
│   └── workflow.py     # LangGraph 状态机编排
├── cli/                # Typer 命令行入口
├── docker/             # Docker 部署配置 (Dockerfile, Compose)
├── scripts/            # 辅助脚本（数据加载、环境验证等）
├── templates/          # 模板库 (Plan YAML, Jinja2 Reports)
├── tests/              # 自动化测试用例
├── main.py             # CLI 快捷入口
└── pyproject.toml      # 项目元数据与依赖管理
```

## 🚀 快速开始

### 1. 环境准备

推荐使用 [uv](https://github.com/astral-sh/uv) 管理环境（速度极快）：

```bash
# 自动创建并安装依赖
uv sync --all-extras
source .venv/bin/activate
```

或使用传统 `pip`：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev,data]
```

### 2. 配置环境变量

复制 `.env.example` 并配置关键参数：

```bash
cp .env.example .env
```

**关键配置项：**

- `MODEL`: LLM 模型名称 (例如 `Qwen/Qwen3-30B-A3B-Instruct-2507`)
- `MODEL_BASE_URL`: OpenAI 兼容的 API 地址
- `OPENAI_API_KEY`: API 密钥
- `MYSQL_URL`: 数据库连接串（例如 `mysql+pymysql://user:pass@host:3306/db`）
- `RUNS_DIR`: 运行产物存储目录 (默认 `./runs`)
- `LLM_FAKE=1`: 开启离线模拟模式（无需真实 LLM）
- `PDF_BACKEND`: PDF 渲染后端 (默认 `weasyprint`)
- `ENABLE_EXPLAIN`: 是否开启 SQL 执行计划分析 (默认 `True`)

### 3. 运行方式

#### A. 命令行交互 (CLI)
```bash
# 启动交互式分析任务
autoplan-agent run "分析过去30天订单退款率异常的原因"

# 继续执行中断的任务 (基于 run_id)
autoplan-agent resume <run_id>

# 查看/重新生成报告
autoplan-agent report <run_id> --fmt pdf
```

#### B. API 服务
```bash
# 启动服务
autoplan-agent serve --port 8000

# API 调用示例
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"user_task":"分析近期支付失败率情况"}'
```

#### C. Docker 部署
```bash
# 一键启动 MySQL 演示库与 Agent 服务
cd docker
docker-compose up -d
```

## 🛠️ 核心工作流

系统基于 **LangGraph** 构建，实现了带有人机交互（Human-in-the-loop）的状态机：

1. **Understand**: 结合数据库 Schema Hint，利用 LLM 解析需求，产出 `TaskUnderstandingReport`。
2. **Apply Feedback**: 若用户提供修改意见，系统将更新任务理解并标记旧计划失效。
3. **Plan**: 结合 `template_id` (YAML) 与理解报告，自动生成多步骤 `ExecutionPlan`。
4. **Confirm**: 状态机进入 `NEEDS_CONFIRMATION`，等待用户审批或反馈。
5. **Execute**: 遍历计划步骤，按序调用工具箱，实时产出 `Artifacts`（Parquet/JSON/Images）。
6. **Report**: 汇总执行产物，基于 Jinja2 模板渲染生成 Markdown/HTML/PDF 专业分析报告。

## 🧩 扩展与自定义

- **自定义计划模板**：在 `templates/plans/` 下添加 YAML，定义各步骤的默认工具与依赖关系。
- **自定义业务规则**：在 `templates/business_rules/` 中定义行业特定的计算逻辑或约束。
- **自定义工具插件**：通过 `PLUGINS_DIR` 动态加载 Python 工具包。
- **多模型适配**：在 [utils.py](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/utils.py) 中扩展 `get_model_from_name` 以支持更多 LLM 供应商。

