"""提示词管理模块。

该模块提供基于 Jinja2 的提示词模板环境配置。
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def get_prompt_env(base_dir: Path) -> Environment:
    """获取 Jinja2 模板环境。

    Args:
        base_dir: 模板文件所在目录。

    Returns:
        Environment: 配置好的 Jinja2 环境。
    """
    return Environment(
        loader=FileSystemLoader(str(base_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
