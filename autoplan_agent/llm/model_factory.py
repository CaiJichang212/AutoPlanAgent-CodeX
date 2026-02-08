"""LLM 模型工厂模块。

该模块负责根据配置创建并返回合适的 LLM 实例。
"""

import json
import os
from typing import Any, List

from langchain_core.messages import AIMessage

from autoplan_agent.config import Settings


class StaticJsonLLM:
    """提供静态 JSON 响应的伪造 LLM。"""

    def __init__(self, responses: List[str]):
        """初始化。

        Args:
            responses: 预设的响应字符串列表。
        """
        self._responses = responses

    def invoke(self, messages: Any) -> AIMessage:
        """调用伪造 LLM。

        Args:
            messages: 输入消息。

        Returns:
            AIMessage: 包含预设内容的 AIMessage 对象。
        """
        if self._responses:
            content = self._responses.pop(0)
        else:
            content = "{}"
        return AIMessage(content=content)


def _load_utils():
    """尝试加载项目根目录下的 utils 模块。

    Returns:
        module: utils 模块，如果加载失败则返回 None。
    """
    try:
        import utils  # type: ignore

        return utils
    except Exception:
        return None


def get_llm(settings: Settings):
    """获取配置好的 LLM 实例。

    Args:
        settings: 应用配置。

    Returns:
        LLM: 适配后的 LLM 实例。

    Raises:
        RuntimeError: 如果未配置有效的 LLM。
    """
    if settings.llm_fake:
        raw = os.getenv("LLM_FAKE_JSON", "{}")
        try:
            json.loads(raw)
        except Exception:
            raw = "{}"
        return StaticJsonLLM([raw])

    utils = _load_utils()
    if utils and hasattr(utils, "get_model_from_name"):
        try:
            return utils.get_model_from_name(
                model=settings.model,
                base_url=settings.model_base_url,
            )
        except Exception:
            pass

    try:
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("MODELSCOPE_API_KEYS", "").split(",")[0]
        if not api_key:
            raise RuntimeError("Missing API key for ChatOpenAI")
        return ChatOpenAI(
            model=settings.model,
            api_key=api_key,
            base_url=settings.model_base_url,
        )
    except Exception as exc:
        raise RuntimeError("No LLM configured. Set LLM_FAKE=1 or provide MODEL settings.") from exc
