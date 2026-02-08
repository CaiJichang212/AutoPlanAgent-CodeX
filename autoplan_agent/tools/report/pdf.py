"""PDF 渲染工具模块。

该模块提供将 HTML 报告转换为 PDF 文件的功能，支持 WeasyPrint 和 Matplotlib 两种后端。
"""

import html
import re
import textwrap
import warnings
from ctypes.util import find_library
from pathlib import Path


class PdfBackend:
    """PDF 渲染后端基类。"""
    def render(self, html_path: Path, output_path: Path) -> Path:
        """渲染 HTML 为 PDF。

        Args:
            html_path: 输入 HTML 文件路径。
            output_path: 输出 PDF 文件路径。

        Returns:
            Path: 输出 PDF 文件路径。
        """
        raise NotImplementedError


class WeasyPrintBackend(PdfBackend):
    """基于 WeasyPrint 的 PDF 渲染后端。"""
    def render(self, html_path: Path, output_path: Path) -> Path:
        """使用 WeasyPrint 渲染 PDF，如果环境不支持则回退到 Matplotlib。"""
        if not _can_use_weasyprint_runtime():
            return MatplotlibPdfBackend().render(html_path, output_path)
        try:
            from weasyprint import HTML

            HTML(filename=str(html_path)).write_pdf(str(output_path))
            return output_path
        except Exception:
            # Fallback when native WeasyPrint runtime deps are missing.
            return MatplotlibPdfBackend().render(html_path, output_path)


class MatplotlibPdfBackend(PdfBackend):
    """基于 Matplotlib 的轻量级 PDF 渲染后端（作为回退方案）。"""
    def render(self, html_path: Path, output_path: Path) -> Path:
        """将 HTML 转换为纯文本并使用 Matplotlib 绘制到 PDF。"""
        from matplotlib import pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        raw_html = html_path.read_text(encoding="utf-8", errors="ignore")
        text = _html_to_text(raw_html)
        lines = _wrap_lines(text, width=96)
        if not lines:
            lines = ["(empty report)"]

        max_lines_per_page = 52
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"Glyph .* missing from font")
            with PdfPages(output_path) as pdf:
                for start in range(0, len(lines), max_lines_per_page):
                    page_lines = lines[start : start + max_lines_per_page]
                    fig = plt.figure(figsize=(8.27, 11.69))
                    fig.text(
                        0.06,
                        0.97,
                        "\n".join(page_lines),
                        va="top",
                        ha="left",
                        fontsize=9,
                        family="sans-serif",
                    )
                    plt.axis("off")
                    pdf.savefig(fig, bbox_inches="tight")
                    plt.close(fig)
        return output_path


def _html_to_text(content: str) -> str:
    """简单的 HTML 转纯文本转换。"""
    content = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", "", content)
    content = re.sub(r"(?i)<br\\s*/?>", "\n", content)
    content = re.sub(r"(?i)</p\\s*>", "\n\n", content)
    content = re.sub(r"(?is)<[^>]+>", "", content)
    content = html.unescape(content)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _wrap_lines(text: str, width: int) -> list[str]:
    """对文本行进行自动换行处理。"""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            lines.append("")
            continue
        wrapped = textwrap.wrap(line, width=width) or [line]
        lines.extend(wrapped)
    return lines


def _can_use_weasyprint_runtime() -> bool:
    """检查当前环境是否具备运行 WeasyPrint 所需的动态库。"""
    # WeasyPrint relies on these shared libs. If missing, importing weasyprint
    # emits noisy warnings; skip import and use fallback backend directly.
    required = ["gobject-2.0", "pango-1.0", "pangocairo-1.0"]
    return all(find_library(name) for name in required)


def get_pdf_backend(name: str) -> PdfBackend:
    """获取指定名称的 PDF 渲染后端实例。

    Args:
        name: 后端名称 ('weasyprint' 或 'matplotlib')。

    Returns:
        PdfBackend: 后端实例。

    Raises:
        ValueError: 如果后端名称不受支持。
    """
    if name == "weasyprint":
        return WeasyPrintBackend()
    if name == "matplotlib":
        return MatplotlibPdfBackend()
    raise ValueError(f"Unsupported PDF backend: {name}")
