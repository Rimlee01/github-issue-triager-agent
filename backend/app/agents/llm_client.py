"""
LLM client using Groq via langchain-groq.
"""
from __future__ import annotations

import json
import re

from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_llm: ChatGroq | None = None


class LLMOutputParseError(Exception):
    pass


def get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
            api_key=settings.GROQ_API_KEY,
            max_tokens=2000,
        )
    return _llm


def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMOutputParseError(f"Could not parse JSON: {exc}\nRaw: {raw_text[:500]}")

    raise LLMOutputParseError(f"No JSON found. Raw: {raw_text[:500]}")


async def call_llm_json(prompt: str) -> dict:
    llm = get_llm()
    response = await llm.ainvoke(prompt)
    raw = response.content if isinstance(response.content, str) else str(response.content)
    try:
        return extract_json(raw)
    except LLMOutputParseError:
        logger.warning("llm_json_parse_failed_retrying")
        retry_prompt = (
            prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object, no other text."
        )
        response = await llm.ainvoke(retry_prompt)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        return extract_json(raw)


async def call_llm_text(prompt: str) -> str:
    llm = get_llm()
    response = await llm.ainvoke(prompt)
    return response.content if isinstance(response.content, str) else str(response.content)
