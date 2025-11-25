import base64
import os
from pathlib import Path
import traceback

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.genai.chats import Chat
from typing import Dict, List


class LLMChatClient:

    def __init__(self, model, system_instructions: str):
        # Setup
        self.GCP_PROJECT = os.environ["GCP_PROJECT"]
        self.GCP_LOCATION = os.environ["GCP_REGION"]
        self.GENERATIVE_MODEL = "gemini-2.0-flash-001"

        #############################################################################
        #                       Initialize the LLM Client                           #
        self.llm_client = genai.Client(
            vertexai=True, project=self.GCP_PROJECT, location=self.GCP_LOCATION
        )

    def create_chat_session(self, past_history=None) -> Chat:
        return self.llm_client.chats.create(
            model=self.GENERATIVE_MODEL,
            history=past_history,
        )

    def generate_response(self, chat_session: Chat, message: Dict) -> str:
        try:
            message_parts = []
            print("HI! message:", message)
            if message.get("image"):
                try:
                    base64_string = message.get("image")
                    if "," in base64_string:
                        header, base64_data = base64_string.split(",", 1)
                        mime_type = header.split(";")[0].split("/")[0]
                    else:
                        base64_data = base64_string
                        mime_type = "image/jpeg"

                    # Decode base64 to bytes
                    image_bytes = base64.b64decode(base64_data)
                    # Create image Part using FileData
                    image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
                    message_parts.append(image_part)

                    # add text content if present
                    if message.get("content"):
                        message_parts.append(message["content"])
                    else:
                        message_parts.append(
                            "Describe the physical characteristics of the building and urban context of the property."
                        )
                except Exception as e:
                    print(f"Error adding image to message parts: {e}")
                    traceback.print_exc()
                    return None
            elif message.get("image_path"):
                # Read the image file
                image_path = os.path.join(
                    "chat-history", "llm", message.get("image_path")
                )
                with Path(image_path).open("rb") as f:
                    image_bytes = f.read()
                mime_type = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".tiff": "image/tiff",
                    ".ico": "image/x-icon",
                    ".webp": "image/webp",
                    ".svg": "image/svg+xml",
                    ".heic": "image/heic",
                    ".heif": "image/heif",
                }.get(Path(image_path).suffix.lower(), "image/jpeg")

                image_part = Part.from_bytes(data=image_bytes, mime_type=mime_type)
                message_parts.append(image_part)

                # Add text content if present
                if message.get("content"):
                    message_parts.append(message["content"])
                else:
                    message_parts.append(
                        "Describe the physical characteristics of the building and urban context of the property."
                    )
            else:
                # Add text content if present
                if message.get("content"):
                    message_parts.append(message["content"])

            if not message_parts:
                raise ValueError("No message parts provided")

            response = chat_session.send_message(message_parts)
            return response.text
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            traceback.print_exc()
            raise ValueError(f"Failed to generate response: {str(e)}")

    def rebuild_chat_session(self, chat_history: List[Dict]) -> Chat:
        """Rebuild the chat session from the chat history"""
        formatted_history = []
        for message in chat_history:
            if message["role"] == "user":
                formatted_history.append(
                    types.UserContent(parts=[Part.from_text(text=message["content"])])
                )
            elif message["role"] == "assistant":
                formatted_history.append(
                    types.ModelContent(parts=[Part.from_text(text=message["content"])])
                )

        new_session = self.create_chat_session(formatted_history)
        return new_session
