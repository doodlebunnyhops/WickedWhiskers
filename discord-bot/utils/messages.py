import json
import os
import random
import settings

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

            # Format the message with any provided kwargs
            logger.debug(f"Message: {message}")
            return message.format(**kwargs)

        except (KeyError, TypeError) as e:
            logger.error(f"Error Key Error message: {str(e)}\n\tKeys: {keys}")
            return default
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return f"Error formatting message: {str(e)}"
