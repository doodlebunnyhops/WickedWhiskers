import json
import os
import random
import settings
from functools import lru_cache
from pathlib import Path

logger = settings.logging.getLogger("bot")

class MessageLoader:
    def __init__(self, file_path: str):
        self.messages = {}
        self.file_path = file_path
        self.load_messages()

    def load_messages(self):
        """Load messages from a JSON file into memory."""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
        else:
            raise FileNotFoundError(f"Message file {self.file_path} not found.")

    def get_message(self, *keys, default="Message not found", **kwargs):
        """Get a message by providing nested keys. If a list is found, pick a random one, and always format when {user}, {target} or {amount} are found"""
        message = self.messages
        try:
            for key in keys:
                if isinstance(key, int):
                    key = str(key)  # Handle numeric keys
                message = message[key]

            # If the message is a list, randomly pick one
            if isinstance(message, list):
                message = random.choice(message)

            # Artwork aliases keep each CDN URL in one place.
            if isinstance(message, str) and message.startswith("asset:"):
                message = self.messages["artwork"][message[6:]]

            # Format the message with any provided kwargs
            logger.debug(f"Message: {message}")
            return message.format(**kwargs)

        except (KeyError, TypeError) as e:
            logger.error(f"Error Key Error message: {str(e)}\n\tKeys: {keys}")
            return default
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return f"Error formatting message: {str(e)}"
        
    def get_message_block(self, *keys, default=None):
        """Get a block of messages by providing nested keys. Returns the block or default if not found."""
        message = self.messages
        try:
            for key in keys:
                if isinstance(key, int):
                    key = str(key)  # Handle numeric keys
                message = message[key]
            
            # Check if it's a dictionary or valid block
            if isinstance(message, dict):
                return message
            else:
                logger.error(f"The message block {keys} is not a valid dictionary.")
                return default
        except KeyError as e:
            logger.error(f"Error accessing message block: {str(e)}\n\tKeys: {keys}")
            return default
        except Exception as e:
            logger.error(f"Unexpected error accessing message block: {str(e)}")
            return default


@lru_cache(maxsize=1)
def default_messages():
    """One in-memory catalog, independent of the process working directory."""
    return MessageLoader(str(Path(__file__).with_name('messages.json')))
