from agents import Agent

from backend.agents.client import get_agent_model
from backend.agents.context import AgentContext
from backend.agents.prompt_loader import load_system_prompt
from backend.agents.tools import retrieve_documents


def build_agent() -> Agent[AgentContext]:
    return Agent[AgentContext](
        name="rag-assistant",
        instructions=load_system_prompt(),
        model=get_agent_model(),
        tools=[retrieve_documents],
    )
