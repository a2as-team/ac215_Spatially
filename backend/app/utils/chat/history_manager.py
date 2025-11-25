import json
from optparse import Option
import os
from pathlib import Path
import trace
from typing import Dict, List, Optional
import glob
import base64
import traceback
from pydantic import BaseModel, Field

PERSISTENT_DIR = "/persistent"


class ChatMessage(BaseModel):
    content: Optional[str] = Field(None, description="The message content")
    image: Optional[str] = Field(None, description="The image content")
    message_id: Optional[str] = Field(None, description="The message id")
    role: Optional[str] = Field(None, description="The role")


class ChatHistoryManager:
    def __init__(self, model, history_dir: str = "chat-history"):
        self.model = model
        self.history_dir = os.path.join(PERSISTENT_DIR, history_dir, model)
        self.images_dir = os.path.join(self.history_dir, "images")
        self._ensure_directories()

    def _ensure_directories(self):
        os.makedirs(self.history_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

    def _get_chat_filepath(self, chat_id: str, session_id: str) -> str:
        return os.path.join(self.history_dir, session_id, f"{chat_id}.json")

    def _save_image(self, chat_id: str, message_id: str, image_data: str) -> str:
        chat_images_dir = os.path.join(self.images_dir, chat_id)
        os.makedirs(chat_images_dir, exist_ok=True)

        image_path = Path(chat_images_dir) / f"{message_id}.png"
        try:
            base64_string = image_data
            if "," in base64_string:
                header, base64_data = base64_string.split(",", 1)
                mime_type = header.split(";")[0].split("/")[-1]
            else:
                base64_data = base64_string
                mime_type = "image/jpeg"

            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(image_data))

            return os.path.relpath(image_path, self.history_dir)
        except Exception as e:
            print("Error saving image: ", e)
            traceback.print_exc()

    def _load_image(self, relative_path: str) -> str:
        full_path = Path(self.history_dir) / relative_path
        try:
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            else:
                return None
        except Exception as e:
            print("Error loading image: ", e)
            traceback.print_exc()
            return None

    def save_chat(self, chat_to_save: Dict, session_id: str) -> None:
        chat_dir = os.path.join(self.history_dir, session_id)
        os.makedirs(chat_dir, exist_ok=True)
        for message in chat_to_save["messages"]:
            if "image" in message and message["image"] is not None:
                image_path = self._save_image(
                    chat_to_save["chat_id"], message["message_id"], message["image"]
                )
                if image_path:
                    message["image_path"] = image_path
                del message["image"]
        filepath = self._get_chat_filepath(chat_to_save["chat_id"], session_id)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving chat: ", e)
            traceback.print_exc()
            return None
        return True

    def get_chat(self, chat_id: str, session_id: str) -> Optional[Dict]:
        filepath = os.path.join(self.history_dir, session_id, f"{chat_id}.json")
        chat_data = {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
        except Exception as e:
            print(f"Error loading chat history from {filepath}: {e}")
            traceback.print_exc()
        return chat_data

    def get_recent_chats(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        chat_dir = os.path.join(self.history_dir, session_id)
        os.makedirs(chat_dir, exist_ok=True)
        recent_chats = []

        chat_files = glob.glob(os.path.join(chat_dir, "*.json"))
        for filepath in chat_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                    recent_chats.append(chat_data)
            except Exception as e:
                print(f"Error loading chat history from {filepath}: {e}")
                traceback.print_exc()
        recent_chats.sort(key=lambda x: x.get("dts", 0), reverse=True)
        if limit:
            return recent_chats[:limit]
        return recent_chats
