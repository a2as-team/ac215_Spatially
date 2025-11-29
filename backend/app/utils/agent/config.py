from google.adk.agents import LlmAgent


class AgentConfig:
    def __init__(self):
        self.gemini_agent = LlmAgent(
            name="GeminiAgent",
            model="gemini-2.0-flash",
            instruction="You are a helpful assistant.",
        )
