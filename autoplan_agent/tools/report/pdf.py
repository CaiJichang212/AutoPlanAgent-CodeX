import html
import re
import textwrap
import warnings
from ctypes.util import find_library
from pathlib import Path


class PdfBackend:
    def render(self, html_path: Path, output_path: Path) -> Path:
        raise NotImplementedError


class WeasyPrintBackend(PdfBackend):
    def render(self, html_path: Path, output_path: Path) -> Path:
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
    def render(self, html_path: Path, output_path: Path) -> Path:
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
    content = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", "", content)
    content = re.sub(r"(?i)<br\\s*/?>", "\n", content)
    content = re.sub(r"(?i)</p\\s*>", "\n\n", content)
    content = re.sub(r"(?is)<[^>]+>", "", content)
    content = html.unescape(content)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _wrap_lines(text: str, width: int) -> list[str]:
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
    # WeasyPrint relies on these shared libs. If missing, importing weasyprint
    # emits noisy warnings; skip import and use fallback backend directly.
    required = ["gobject-2.0", "pango-1.0", "pangocairo-1.0"]
    return all(find_library(name) for name in required)


def get_pdf_backend(name: str) -> PdfBackend:
    if name == "weasyprint":
        return WeasyPrintBackend()
    if name == "matplotlib":
        return MatplotlibPdfBackend()
    raise ValueError(f"Unsupported PDF backend: {name}")
