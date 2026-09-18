from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.config import settings


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.0) -> ChatDeepSeek:
    """返回全局唯一的 DeepSeek LLM 实例"""
    if not settings.deepseek_api_key or settings.deepseek_api_key.startswith("sk-请"):
        raise RuntimeError("请先在 .env 中填写 DEEPSEEK_API_KEY")

    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=temperature,
    )


def get_llm_reasoner() -> ChatDeepSeek:
    """推理增强版，需要时单独调用（模型名写死在 env 里也行）"""
    return ChatDeepSeek(
        model="deepseek-reasoner",
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=0.0,
    )