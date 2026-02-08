"""LLM 运行时模块。

该模块提供调用 LLM 和解析 JSON 响应的工具函数。
"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


def call_llm(llm, system_prompt: str, user_prompt: str) -> str:
    """调用 LLM 并返回文本响应。

    Args:
        llm: LLM 实例。
        system_prompt: 系统提示词。
        user_prompt: 用户提示词。

    Returns:
        str: LLM 返回的文本内容。
    """
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    resp = llm.invoke(messages)
    content = getattr(resp, "content", None)
    if content is None:
        return str(resp)
    return content


def parse_json(text: str) -> dict[str, Any]:
    """尝试从文本中解析 JSON 对象。

    支持解析被 Markdown 代码块包裹的 JSON。

    Args:
        text: 待解析的文本。

    Returns:
        dict[str, Any]: 解析后的字典，如果解析失败则返回空字典。
    """
    try:
        return json.loads(text)
    except Exception:
        text = text.strip()
        if text.startswith("```"):
            # 移除 Markdown 代码块标记
            lines = text.splitlines()
            if len(lines) > 2 and lines[0].startswith("```"):
                text = "\n".join(lines[1:-1])
            else:
                text = text.strip("`")
        try:
            return json.loads(text)
        except Exception:
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return json.loads(text[start : end + 1])
            except Exception:
                pass
            return {}
