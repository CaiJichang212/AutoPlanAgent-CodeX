import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


def call_llm(llm, system_prompt: str, user_prompt: str) -> str:
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    resp = llm.invoke(messages)
    content = getattr(resp, "content", None)
    if content is None:
        return str(resp)
    return content


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        text = text.strip()
        if text.startswith("```"):
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
