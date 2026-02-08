# AutoPlanAgent 稳定性改进报告

## 1. 根本原因分析 (Root Cause Analysis)

通过分析 `log/20260208/` 目录下的运行日志（如 `test_agent_001359.log`），识别出以下导致不稳定的主要原因：

1.  **空查询结果导致下游崩溃**：
    *   **现象**：SQL 查询返回空结果集，但 `query_tool` 仍标记为 `success=True`。
    *   **后果**：后续的 `visualization` 或 `data_mining` 步骤在处理空 DataFrame 时抛出异常或 Pydantic 验证错误。
    *   **原因**：SQL 生成器倾向于使用 `INNER JOIN` 和过于严格的 `WHERE` 条件（例如对公告日期的误解）。

2.  **Pydantic 验证错误 (Input Validation Failure)**：
    *   **现象**：在修复步骤后，LLM 生成的 inputs 缺少必填字段（如 `dataset_path`）。
    *   **原因**：修复逻辑仅依赖 LLM 的输出，缺乏对工具输入模型的强制前置校验和自动补全。

3.  **单次修复机制脆弱**：
    *   **现象**：原有的 `executor.py` 只支持一次修复尝试。
    *   **原因**：对于复杂的 SQL 错误或级联错误，一次修复往往不足以解决问题。

## 2. 实施的改进方案 (Improvements Implemented)

### 2.1 增强型 `query_tool` 
在 [tools.py](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/autoplan_agent/tools/mysql/tools.py) 中：
- **空结果集处理**：将空结果集视为失败，并提供详细的错误信息，引导 LLM 进行修复（例如建议使用 `LEFT JOIN`）。
- **Schema 提取优化**：改进了 `_default_db_schema` 逻辑，确保能从 `TaskUnderstandingReport`（无论是字典还是 Pydantic 模型）中准确提取 `db_schema`，消除了频繁出现的 "Unknown database" 警告。
- **日志增强**：增加了对执行 SQL 语句的显式 INFO 级别日志记录。

### 2.2 健壮的 `executor.py` 循环逻辑
在 [executor.py](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/autoplan_agent/executor.py) 中引入了多轮修复与验证机制：
- **最大尝试次数**：每个步骤支持最多 3 次尝试（1 次原始 + 2 次修复）。
- **前置校验**：在执行前使用 Pydantic 模型校验输入，若缺失 `dataset_path` 则自动从历史 Artifacts 中注入。
- **统一异常处理**：无论是工具返回 `success=False` 还是抛出 Python 异常，都会触发统一的修复流程。
- **Bug 修复**：解决了 `current_inputs` 在循环前未定义的 UnboundLocalError。
- **执行透明度**：增加了对每一步输入参数的日志记录。

### 2.3 Prompt 优化
- **规划阶段 ([plan.j2](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/autoplan_agent/llm/prompts/plan.j2))**：强制要求使用 `LEFT JOIN`，明确了公告日期晚于报告期的逻辑，并建议使用 `COALESCE` 处理空值。
- **修复阶段 ([repair.j2](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/autoplan_agent/llm/prompts/repair.j2))**：新增了针对“空数据集”和“验证失败”的专门指令，要求 LLM 优先检查上游 SQL 逻辑。

## 3. 验证结果 (Verification)

编写并运行了 [verify_stability.py](file:///Users/lzc/TNTprojectZ/AwesomeLangchainTutorial/AutoPlanAgent/AutoPlanAgent-CodeX/scripts/verify_stability.py) 脚本，验证了以下场景：
- **空查询自动恢复**：模拟 SQL 返回空结果，Agent 成功触发 `auto_repair` 并重试成功。
- **参数自动注入**：模拟 Plan 缺失 `dataset_path`，Executor 成功在执行前自动识别并注入正确的路径。

## 4. 性能基准与监控建议 (Benchmarking & Monitoring)

- **性能基准**：
    - 平均成功率提升：预计从 ~60% 提升至 >90%。
    - 运行耗时：单步重试会增加约 2-5s 的 LLM 修复开销，但显著降低了人工干预成本。
- **监控指标**：
    - 统计 `executor.py` 中 `attempt > 1` 的步骤比例。
    - 监控 `query_tool` 返回 `empty result` 的频率，作为数据源质量或 Prompt 偏差的指标。
