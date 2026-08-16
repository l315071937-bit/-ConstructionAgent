"""LLMFactory：所有 LLM 调用统一入口（01 27）。provider 增删只改本文件。"""
from openai import OpenAI

from config import settings
from core.logger import get_logger

logger = get_logger("llm_factory")


class LLMClient:
    def __init__(self):
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY 未配置：请在项目根 .env 中设置对应 API 密钥")
        self._client = OpenAI(api_key=settings.llm_api_key,
                              base_url=settings.llm_api_base,
                              timeout=60, max_retries=2)

    def chat(self, messages: list, temperature: float | None = None,
             max_tokens: int | None = None) -> str:
        resp = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def chat_stream(self, messages: list):
        stream = self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


_llm = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        if not settings.llm_api_key:
            logger.warning("LLM_API_KEY 未配置，调用将失败")
        _llm = LLMClient()
    return _llm
