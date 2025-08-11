import asyncio
from agents.screening_decision.agent import ScreeningDecisionAgent
from anthropic import AsyncAnthropic
from config import settings
from db.models.chat import Conversation

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

agent = ScreeningDecisionAgent(client)


async def main():
    messages = await agent.get_messages(conversation_id="123")
    await agent.process_message(message=messages, conversation_id="123", context={})


if __name__ == "__main__":
    asyncio.run(main())
