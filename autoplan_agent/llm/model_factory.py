import json
import os
from typing import Any, List

from langchain_core.messages import AIMessage

from autoplan_agent.config import Settings


class StaticJsonLLM:
    def __init__(self, responses: List[str]):
        self._responses = responses

    def invoke(self, messages: Any) -> AIMessage:
        if self._responses:
            content = self._responses.pop(0)
        else:
            content = "{}"
        return AIMessage(content=content)


def _load_utils():
    try:
        import utils  # type: ignore

        return utils
    except Exception:
        return None


def get_llm(settings: Settings):
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
