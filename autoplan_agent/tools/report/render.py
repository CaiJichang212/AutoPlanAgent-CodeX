from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _env(templates_dir: Path) -> Environment:
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=select_autoescape())


def render_markdown(templates_dir: Path, context: Dict[str, Any], output_path: Path) -> Path:
    env = _env(templates_dir)
    template = env.get_template("report.md.j2")
    output_path.write_text(template.render(**context), encoding="utf-8")
    return output_path


def render_html(templates_dir: Path, context: Dict[str, Any], output_path: Path) -> Path:
    env = _env(templates_dir)
    template = env.get_template("report.html.j2")
    output_path.write_text(template.render(**context), encoding="utf-8")
    return output_path

