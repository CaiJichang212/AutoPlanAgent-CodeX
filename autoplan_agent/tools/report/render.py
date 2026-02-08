"""报告渲染工具模块。

该模块提供使用 Jinja2 模板渲染 Markdown 和 HTML 报告的功能。
"""

from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _env(templates_dir: Path) -> Environment:
    """初始化 Jinja2 环境。"""
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=select_autoescape())


def render_markdown(templates_dir: Path, context: Dict[str, Any], output_path: Path) -> Path:
    """渲染 Markdown 报告。

    Args:
        templates_dir: 模板目录路径。
        context: 模板渲染上下文变量。
        output_path: 输出文件路径。

    Returns:
        Path: 输出文件路径。
    """
    env = _env(templates_dir)
    template = env.get_template("report.md.j2")
    output_path.write_text(template.render(**context), encoding="utf-8")
    return output_path


def render_html(templates_dir: Path, context: Dict[str, Any], output_path: Path) -> Path:
    """渲染 HTML 报告。

    Args:
        templates_dir: 模板目录路径。
        context: 模板渲染上下文变量。
        output_path: 输出文件路径。

    Returns:
        Path: 输出文件路径。
    """
    env = _env(templates_dir)
    template = env.get_template("report.html.j2")
    output_path.write_text(template.render(**context), encoding="utf-8")
    return output_path

