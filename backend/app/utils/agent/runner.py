import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from utils.agent.config import AgentConfig

session_service = InMemorySessionService()


class AgentRunner:
    def __init__(self):
        agent = AgentConfig().gemini_agent
        self.runner = Runner(
            app_name="production-agent", agent=agent, session_service=session_service
        )

    async def run(self, user_message: str) -> str:
        """Run agent and return complete response"""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        await session_service.create_session(
            app_name="production-agent",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

        message = types.Content(role="user", parts=[types.Part(text=user_message)])

        response_text = None
        async for event in self.runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text

        return response_text

    async def run_stream(self, user_message: str):
        """Run agent and stream response chunks"""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        await session_service.create_session(
            app_name="production-agent",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

        message = types.Content(role="user", parts=[types.Part(text=user_message)])

        async for event in self.runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            if event.is_final_response():
                yield event.content.parts[0].text
