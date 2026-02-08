"""Pytest 测试配置模块。

该模块将项目根目录添加到系统路径，确保测试可以正确导入项目包。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
