"""Chat history persistence for agents.

This module provides disk-based persistence for agent chat history.
Stores chat sessions as JSON files in the /persistent directory.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import glob
import base64
import traceback

PERSISTENT_DIR = "/persistent"


class ChatHistoryManager:
    """Manages persistent storage of chat history for agents.

    Stores chat sessions as JSON files organized by:
    /persistent/chat-history/{model}/{session_id}/{chat_id}.json

    Also handles image storage separately to keep JSON files lightweight.
    """

    def __init__(self, model: str, history_dir: str = "chat-history"):
        """
        Initialize the history manager.

        Args:
            model: Model name (used for directory organization)
            history_dir: Base directory name under /persistent
        """
        self.model = model
        self.history_dir = os.path.join(PERSISTENT_DIR, history_dir, model)
        self.images_dir = os.path.join(self.history_dir, "images")
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        os.makedirs(self.history_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

    def _get_chat_filepath(self, chat_id: str, session_id: str) -> str:
        """Get the file path for a chat."""
        return os.path.join(self.history_dir, session_id, f"{chat_id}.json")

    def _save_image(self, chat_id: str, message_id: str, image_data: str) -> Optional[str]:
        """
        Save an image to disk.

        Args:
            chat_id: Chat ID
            message_id: Message ID
            image_data: Base64 encoded image data

        Returns:
            Relative path to saved image, or None on error
        """
        chat_images_dir = os.path.join(self.images_dir, chat_id)
        os.makedirs(chat_images_dir, exist_ok=True)

        image_path = Path(chat_images_dir) / f"{message_id}.png"
        try:
            base64_string = image_data
            if "," in base64_string:
                _, base64_data = base64_string.split(",", 1)
            else:
                base64_data = base64_string

            image_bytes = base64.b64decode(base64_data)
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            return os.path.relpath(image_path, self.history_dir)
        except Exception as e:
            print("Error saving image: ", e)
            traceback.print_exc()
            return None

    def _load_image(self, relative_path: str) -> Optional[str]:
        """
        Load an image from disk.

        Args:
            relative_path: Relative path to the image

        Returns:
            Base64 encoded image data, or None on error
        """
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

    def save_chat(self, chat_to_save: Dict, session_id: str) -> Optional[bool]:
        """
        Save a chat to disk.

        Args:
            chat_to_save: Chat data with 'chat_id' and 'messages'
            session_id: Session ID

        Returns:
            True on success, None on error
        """
        chat_dir = os.path.join(self.history_dir, session_id)
        os.makedirs(chat_dir, exist_ok=True)

        # Extract and save images separately
        for message in chat_to_save.get("messages", []):
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
            return True
        except Exception as e:
            print("Error saving chat: ", e)
            traceback.print_exc()
            return None

    def get_chat(self, chat_id: str, session_id: str) -> Optional[Dict]:
        """
        Load a chat from disk.

        Args:
            chat_id: Chat ID
            session_id: Session ID

        Returns:
            Chat data dictionary, or empty dict if not found
        """
        filepath = os.path.join(self.history_dir, session_id, f"{chat_id}.json")
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading chat history from {filepath}: {e}")
            traceback.print_exc()
            return {}

    def get_recent_chats(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get recent chats for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of chats to return

        Returns:
            List of chat data dictionaries, sorted by timestamp (newest first)
        """
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

    def delete_chat(self, chat_id: str, session_id: str) -> bool:
        """
        Delete a chat from disk.

        Args:
            chat_id: Chat ID
            session_id: Session ID

        Returns:
            True on success, False on error
        """
        filepath = self._get_chat_filepath(chat_id, session_id)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            # Also remove images
            chat_images_dir = os.path.join(self.images_dir, chat_id)
            if os.path.exists(chat_images_dir):
                import shutil
                shutil.rmtree(chat_images_dir)
            return True
        except Exception as e:
            print(f"Error deleting chat: {e}")
            traceback.print_exc()
            return False
