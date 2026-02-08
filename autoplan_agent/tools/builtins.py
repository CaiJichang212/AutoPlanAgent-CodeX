"""内置工具模块。

该模块提供了一系列内置的数据处理、统计分析、挖掘、可视化和报告生成工具。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from pydantic import BaseModel, Field

from autoplan_agent.schemas.artifacts import Artifact, StepResult
from autoplan_agent.tools.dataframe.cleaning import clean_dataframe, coerce_numeric_columns
from autoplan_agent.tools.dataframe.eda import eda_summary
from autoplan_agent.tools.dataframe.io import save_dataframe, preview_dataframe
from autoplan_agent.tools.mining.anomaly import iqr_anomaly, isolation_forest
from autoplan_agent.tools.mining.trend import linear_trend
from autoplan_agent.tools.stats.descriptive import descriptive_stats
from autoplan_agent.tools.stats.correlation import correlation_matrix
from autoplan_agent.tools.stats.hypothesis import t_test, chi_square
from autoplan_agent.tools.viz.plotly_viz import plot_chart as plotly_chart
from autoplan_agent.tools.viz.mpl_viz import plot_chart as mpl_chart
from autoplan_agent.tools.report.render import render_markdown, render_html
from autoplan_agent.tools.report.pdf import get_pdf_backend


class DataframeInput(BaseModel):
    """数据框输入基础模型。

    Attributes:
        dataset_path: 数据集文件路径。
    """
    dataset_path: str


class CleanInput(DataframeInput):
    """数据清洗工具输入模型。

    Attributes:
        rules: 清洗规则字典。
    """
    rules: Dict[str, Any] | None = None


class EDAInput(DataframeInput):
    """EDA 工具输入模型。"""
    pass


class StatsInput(DataframeInput):
    """统计分析工具输入模型。

    Attributes:
        method: 统计方法（如 describe, correlation, t_test, chi_square）。
        col_a: 第一个列名。
        col_b: 第二个列名。
    """
    method: str = "describe"
    col_a: Optional[str] = None
    col_b: Optional[str] = None


class MiningInput(DataframeInput):
    """数据挖掘工具输入模型。

    Attributes:
        method: 挖掘方法（如 iqr, isolation_forest, trend）。
        column: 目标列名。
        columns: 目标列名列表。
        time_col: 时间列名。
        value_col: 数值列名。
    """
    method: str = "iqr"
    column: Optional[str] = None
    columns: Optional[list[str]] = None
    time_col: Optional[str] = None
    value_col: Optional[str] = None


class VizInput(DataframeInput):
    """可视化工具输入模型。

    Attributes:
        spec: 可视化规范字典。
        charts: 图表配置列表。
        backend: 可视化后端（plotly 或 mpl）。
    """
    spec: Dict[str, Any] | None = None
    charts: list[Dict[str, Any] | str] | None = None
    backend: str = "plotly"


class ReportInput(BaseModel):
    """报告生成工具输入模型。

    Attributes:
        summary: 摘要内容。
        findings: 发现内容。
        recommendations: 建议内容。
        data_sources: 数据来源。
        data_quality: 数据质量说明。
        methods: 分析方法。
        appendix: 附录内容。
        understanding: 任务理解对象。
    """
    summary: str
    findings: str
    recommendations: str
    data_sources: str
    data_quality: str
    methods: str
    appendix: str
    understanding: Any | None = None


def _load_df(path: str) -> pd.DataFrame:
    """从路径加载 DataFrame。

    支持 CSV 和 Parquet 格式。

    Args:
        path: 文件路径。

    Returns:
        pd.DataFrame: 加载的数据框。
    """
    p = Path(path)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    return pd.read_csv(p)


def dataframe_clean(inputs: CleanInput, context) -> StepResult:
    """数据清洗工具。

    Args:
        inputs: 清洗参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含清洗后的数据集产物。
    """
    df = _load_df(inputs.dataset_path)
    cleaned = clean_dataframe(df, inputs.rules)
    path, mime = save_dataframe(cleaned, Path(context.run_dir), "cleaned")
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="dataset",
        path=str(path),
        mime_type=mime,
        description="Cleaned dataset",
        preview=preview_dataframe(cleaned),
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="Cleaned dataframe", artifacts=[artifact])


def dataframe_eda(inputs: EDAInput, context) -> StepResult:
    """探索性数据分析 (EDA) 工具。

    Args:
        inputs: EDA 参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含 EDA 摘要产物。
    """
    df = _load_df(inputs.dataset_path)
    if df.empty:
        return StepResult(success=False, message=f"Dataset at {inputs.dataset_path} is empty. Cannot perform EDA.")
    summary = eda_summary(df)
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="summary",
        path="",
        mime_type="application/json",
        description="EDA summary",
        preview=summary,
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="EDA generated", artifacts=[artifact], metrics=summary)


def stats_tool(inputs: StatsInput, context) -> StepResult:
    """统计分析工具。

    Args:
        inputs: 统计分析参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含统计分析结果产物。
    """
    df = _load_df(inputs.dataset_path)
    if df.empty:
        return StepResult(success=False, message=f"Dataset at {inputs.dataset_path} is empty. Cannot perform statistical analysis.")
    result: Dict[str, Any] = {}
    if inputs.method == "correlation":
        result = correlation_matrix(df)
    elif inputs.method == "t_test":
        if not (inputs.col_a and inputs.col_b):
            return StepResult(success=False, message="t_test requires col_a and col_b")
        result = t_test(df, inputs.col_a, inputs.col_b)
    elif inputs.method == "chi_square":
        if not (inputs.col_a and inputs.col_b):
            return StepResult(success=False, message="chi_square requires col_a and col_b")
        result = chi_square(df, inputs.col_a, inputs.col_b)
    else:
        result = descriptive_stats(df)
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="summary",
        path="",
        mime_type="application/json",
        description=f"Stats result ({inputs.method})",
        preview=result,
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="Stats generated", artifacts=[artifact], metrics=result)


def mining_tool(inputs: MiningInput, context) -> StepResult:
    """数据挖掘工具。

    Args:
        inputs: 数据挖掘参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含挖掘出的发现或异常。
    """
    df = _load_df(inputs.dataset_path)
    result: Dict[str, Any] = {}
    
    if inputs.method == "trend" and inputs.time_col and inputs.value_col:
        result = linear_trend(df, inputs.time_col, inputs.value_col)
    elif inputs.method == "isolation_forest":
        df = coerce_numeric_columns(df, inputs.columns)
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cols_to_use = [c for c in (inputs.columns or []) if c in numeric_cols]
        if not cols_to_use:
            # Fallback to all numeric columns if none of specified columns are found/numeric
            cols_to_use = numeric_cols
        
        if not cols_to_use:
            return StepResult(success=False, message="No numeric columns for isolation forest")
            
        result = isolation_forest(df, cols_to_use)
    else:
        df = coerce_numeric_columns(df, inputs.columns)
        numeric_cols = df.select_dtypes(include="number").columns
        if numeric_cols.empty:
            if df.empty:
                return StepResult(success=False, message="Dataset is empty. Cannot perform anomaly detection.")
            return StepResult(success=False, message="No numeric columns found for anomaly detection.")
        
        column = inputs.column
        if not column or column not in df.columns:
            column = numeric_cols[0]
            
        result = iqr_anomaly(df, column)
        
    artifact = Artifact(
        artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
        type="summary",
        path="",
        mime_type="application/json",
        description=f"Mining result ({inputs.method})",
        preview=result,
        created_at=datetime.utcnow().isoformat(),
    )
    return StepResult(success=True, message="Mining generated", artifacts=[artifact], metrics=result)


def viz_tool(inputs: VizInput, context) -> StepResult:
    """数据可视化工具。

    Args:
        inputs: 可视化参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含生成的图表产物。
    """
    df = _load_df(inputs.dataset_path)
    if df.empty:
        return StepResult(
            success=False, 
            message=f"Dataset at {inputs.dataset_path} is empty. This usually means the previous SQL query or cleaning step filtered out all rows. "
                    "If you are repairing this, consider if the SQL query in the data_extraction step was too restrictive (e.g., using INNER JOIN instead of LEFT JOIN, or incorrect ON conditions)."
        )

    run_dir = Path(context.run_dir)
    
    # Collect all specs to process
    specs = []
    if inputs.charts:
        for c in inputs.charts:
            if isinstance(c, dict):
                specs.append(c)
            elif isinstance(c, str):
                # If it's just a name, try to guess a reasonable spec
                specs.append({"title": c, "type": "bar"})
    elif inputs.spec:
        specs.append(inputs.spec)
    
    # If no specs, fallback to default
    if not specs:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            y = numeric_cols[0]
            x = df.columns[0]
            specs.append({"type": "line", "x": x, "y": y, "title": f"{y} trend"})
        else:
            return StepResult(success=False, message="No numeric columns found for visualization")

    all_artifacts = []
    for i, spec in enumerate(specs):
        # Ensure x and y are set if not present
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if "y" not in spec and numeric_cols:
            spec["y"] = numeric_cols[0]
        if "x" not in spec:
            spec["x"] = df.columns[0]
        
        if inputs.backend == "mpl":
            path = mpl_chart(df, spec, run_dir)
            all_artifacts.append(
                Artifact(
                    artifact_id=f"chart_{i}_{datetime.utcnow().timestamp()}",
                    type="chart",
                    path=str(path),
                    mime_type="image/png",
                    description=spec.get("title", "Matplotlib chart"),
                    created_at=datetime.utcnow().isoformat(),
                )
            )
        else:
            html_path, png_path = plotly_chart(df, spec, run_dir)
            all_artifacts.append(
                Artifact(
                    artifact_id=f"chart_html_{i}_{datetime.utcnow().timestamp()}",
                    type="chart",
                    path=str(html_path),
                    mime_type="text/html",
                    description=f"{spec.get('title', 'Plotly chart')} (html)",
                    created_at=datetime.utcnow().isoformat(),
                )
            )
            if png_path.exists():
                all_artifacts.append(
                    Artifact(
                        artifact_id=f"chart_png_{i}_{datetime.utcnow().timestamp()}",
                        type="chart",
                        path=str(png_path),
                        mime_type="image/png",
                        description=f"{spec.get('title', 'Plotly chart')} (png)",
                        created_at=datetime.utcnow().isoformat(),
                    )
                )
    
    return StepResult(success=True, message=f"Generated {len(all_artifacts)} visualization artifacts", artifacts=all_artifacts)


def report_tool(inputs: ReportInput, context) -> StepResult:
    """报告生成工具。

    Args:
        inputs: 报告内容参数。
        context: 工具执行上下文。

    Returns:
        StepResult: 执行结果，包含 Markdown、HTML 和 PDF 报告产物。
    """
    run_dir = Path(context.run_dir)
    templates_dir = Path(context.settings.templates_dir) / "report"
    md_path = run_dir / "artifacts" / "report.md"
    html_path = run_dir / "artifacts" / "report.html"
    render_markdown(templates_dir, inputs.model_dump(), md_path)
    render_html(templates_dir, inputs.model_dump(), html_path)
    artifacts = [
        Artifact(
            artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
            type="report",
            path=str(md_path),
            mime_type="text/markdown",
            description="Markdown report",
            created_at=datetime.utcnow().isoformat(),
        ),
        Artifact(
            artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
            type="report",
            path=str(html_path),
            mime_type="text/html",
            description="HTML report",
            created_at=datetime.utcnow().isoformat(),
        ),
    ]

    try:
        pdf_backend = get_pdf_backend(context.settings.pdf_backend)
        pdf_path = run_dir / "artifacts" / "report.pdf"
        pdf_backend.render(html_path, pdf_path)
        artifacts.append(
            Artifact(
                artifact_id=f"artifact_{datetime.utcnow().timestamp()}",
                type="report",
                path=str(pdf_path),
                mime_type="application/pdf",
                description="PDF report",
                created_at=datetime.utcnow().isoformat(),
            )
        )
    except Exception as exc:
        context.logger.warning("PDF generation failed: %s", exc)

    return StepResult(success=True, message="Report generated", artifacts=artifacts)
