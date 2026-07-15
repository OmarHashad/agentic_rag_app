from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from backend.core.config import OPENROUTER_API_KEY, OPENROUTER_AGENT_MODEL, OPENROUTER_BASE_URL

_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)


def get_agent_model() -> OpenAIChatCompletionsModel:
    return OpenAIChatCompletionsModel(model=OPENROUTER_AGENT_MODEL, openai_client=_client)
