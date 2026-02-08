
import sys
from pathlib import Path
import logging
import pandas as pd
from unittest.mock import MagicMock

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from autoplan_agent.executor import execute_plan
from autoplan_agent.tools import build_registry
from autoplan_agent.tools.registry import ToolContext
from autoplan_agent.config import Settings
from autoplan_agent.schemas.plan import ExecutionPlan, PlanStep
from autoplan_agent.schemas.artifacts import Artifact, StepResult

def test_retry_on_empty_result():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_stability")
    
    settings = Settings()
    registry = build_registry(settings)
    
    # 1. Mock LLM to return a "fixed" SQL when requested
    # The first time it's called for repair, it will return a working SQL
    mock_llm = MagicMock()
    mock_llm.invoke = MagicMock()
    
    # Mocking call_llm behavior
    # We'll use a side_effect to simulate different repair responses
    def mock_call_llm(llm, system, prompt):
        if "SQL query returned empty result" in prompt:
            return '{"sql": "SELECT 1 AS col", "max_rows": 10}'
        return "{}"
    
    import autoplan_agent.executor as executor
    executor.call_llm = mock_call_llm
    
    # 2. Create a plan with a SQL query that will return empty
    # We'll mock the tool itself to return empty first, then succeed
    original_query_tool = registry.get("mysql.query").handler
    
    call_count = 0
    def mocked_query_tool(inputs, context):
        nonlocal call_count
        call_count += 1
        from autoplan_agent.schemas.artifacts import StepResult, Artifact
        if call_count == 1:
            # Simulate empty result
            return StepResult(
                success=False, 
                message="SQL query returned empty result. This often happens due to overly restrictive JOINs (use LEFT JOIN instead of INNER JOIN) or filter conditions. SQL: SELECT * FROM non_existent WHERE 1=0"
            )
        else:
            # Succeed on second attempt with a dummy artifact
            art = Artifact(
                artifact_id="art_1",
                type="dataset",
                path="test.csv",
                mime_type="text/csv",
                description="test",
                created_at="now"
            )
            return StepResult(success=True, message="Success", artifacts=[art])

    registry.get("mysql.query").handler = mocked_query_tool
    
    # Define the plan
    plan = ExecutionPlan(
        plan_id="test_retry",
        run_id="run_test",
        version=1,
        steps=[
            PlanStep(
                step_id="data_extraction",
                name="Data Extraction",
                tool="mysql.query",
                inputs={"sql": "SELECT * FROM non_existent WHERE 1=0"},
                on_error="auto_repair"
            )
        ]
    )
    
    state = {
        "plan": plan,
        "run_id": "run_test",
        "artifacts": [],
        "understanding": MagicMock()
    }
    
    run_path = Path("test_runs")
    run_path.mkdir(exist_ok=True)
    
    # 3. Execute plan
    result = execute_plan(state, registry, settings, logger, run_path, llm=mock_llm)
    
    # 4. Assertions
    print(f"Final status: {result['status']}")
    print(f"Total query tool calls: {call_count}")
    
    assert result["status"] == "DONE"
    assert call_count == 2
    print("Verification SUCCESS: Retry logic handled empty result and recovered.")

def test_fix_missing_dataset_path():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_stability_pydantic")
    
    settings = Settings()
    registry = build_registry(settings)
    
    mock_llm = MagicMock()
    
    # We'll simulate a tool that requires dataset_path
    # but the initial plan misses it
    
    art = Artifact(
        artifact_id="art_1",
        type="dataset",
        path="test_from_prev.csv",
        mime_type="text/csv",
        description="test",
        created_at="now"
    )
    
    # Mock dataframe_clean to succeed
    mock_clean = MagicMock(return_value=MagicMock(success=True, artifacts=[art]))
    registry.get("dataframe.clean").handler = mock_clean
    
    plan = ExecutionPlan(
        plan_id="test_pydantic",
        run_id="run_test_pydantic",
        version=1,
        steps=[
            PlanStep(
                step_id="clean_step",
                name="Cleaning",
                tool="dataframe.clean",
                inputs={}, # MISSING dataset_path
                on_error="auto_repair"
            )
        ]
    )
    
    state = {
        "plan": plan,
        "run_id": "run_test_pydantic",
        "artifacts": [art], # Previous artifact exists
        "understanding": MagicMock()
    }
    
    run_path = Path("test_runs")
    
    # Execute plan
    result = execute_plan(state, registry, settings, logger, run_path, llm=mock_llm)
    
    print(f"Final status: {result['status']}")
    assert result["status"] == "DONE"
    # Verify that dataset_path was injected
    called_inputs = mock_clean.call_args[0][0]
    assert called_inputs.dataset_path == "test_from_prev.csv"
    print("Verification SUCCESS: Missing dataset_path was automatically injected.")

if __name__ == "__main__":
    test_retry_on_empty_result()
    print("-" * 20)
    test_fix_missing_dataset_path()
