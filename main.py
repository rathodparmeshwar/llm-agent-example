import asyncio
from agents.screening_decision.agent import ScreeningDecisionAgent
from anthropic import AsyncAnthropic
from config import settings
from db.models.chat import Conversation
from db.models.chat import Message
from db.session import get_db
from sqlalchemy import select

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

agent = ScreeningDecisionAgent(client)


async def main():
    db = await get_db()
    messages = await db.execute(select(Message).where(Message.conversation_id == "123"))
    await agent.process_message(message=messages, conversation_id="123", context={})


if __name__ == "__main__":
    asyncio.run(main())
