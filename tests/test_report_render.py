from pathlib import Path

from autoplan_agent.schemas.understanding import TaskUnderstandingReport
from autoplan_agent.tools.report.render import render_markdown, render_html


def test_render_report(tmp_path: Path):
    templates_dir = Path("templates/report")
    context = {
        "summary": "summary",
        "findings": "findings",
        "recommendations": "rec",
        "data_sources": "sources",
        "data_quality": "quality",
        "methods": "methods",
        "appendix": "appendix",
        "understanding": TaskUnderstandingReport(analysis_goal="goal"),
    }
    md_path = tmp_path / "report.md"
    html_path = tmp_path / "report.html"
    render_markdown(templates_dir, context, md_path)
    render_html(templates_dir, context, html_path)
    assert md_path.exists()
    assert html_path.exists()
