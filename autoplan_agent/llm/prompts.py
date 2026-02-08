from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


def get_prompt_env(base_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(base_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
