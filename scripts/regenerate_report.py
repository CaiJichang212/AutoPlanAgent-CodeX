
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from autoplan_agent.config import Settings
from autoplan_agent.storage.checkpoint import get_checkpointer
from autoplan_agent.executor import _build_report_inputs
from autoplan_agent.tools.builtins import report_tool
from autoplan_agent.llm.model_factory import get_llm
from autoplan_agent.tools.registry import ToolContext
import logging

def regenerate_report(run_id: str):
    settings = Settings()
    run_path = settings.runs_dir / run_id
    if not run_path.exists():
        print(f"Run directory not found: {run_path}")
        return

    # 1. Get state from checkpoint
    saver = get_checkpointer(run_path)
    config = {"configurable": {"thread_id": run_id}}
    checkpoint_tuple = saver.get_tuple(config)
    if not checkpoint_tuple:
        print(f"No checkpoint found for run_id: {run_id}")
        return
    
    state = checkpoint_tuple.checkpoint["channel_values"]
    
    # 2. Build report inputs (this will use the new Chinese prompts in executor.py)
    llm = get_llm(settings)
    artifacts = state.get("artifacts", [])
    report_inputs = _build_report_inputs(state, artifacts, llm=llm)
    
    # 3. Call report tool
    logger = logging.getLogger("regenerate_report")
    context = ToolContext(
        run_id=run_id,
        run_dir=str(run_path),
        settings=settings,
        logger=logger,
        state=state
    )
    
    from autoplan_agent.tools.builtins import ReportInput
    inputs_obj = ReportInput(**report_inputs)
    result = report_tool(inputs_obj, context)
    
    if result.success:
        print(f"Successfully regenerated report for {run_id}")
        for art in result.artifacts:
            print(f"  - {art.path} ({art.description})")
    else:
        print(f"Failed to regenerate report: {result.message}")

if __name__ == "__main__":
    run_id = "run_6bb4f56b6a2e"
    regenerate_report(run_id)
