import random
import re
from logging import Handler, LogRecord, ERROR, DEBUG
from discord_webhook import DiscordWebhook

from .config import Config


class Discord:
    def __init__(self, config: Config):
        self.discord_webhook = config.discord_webhook

    def uwuizer(self, message: str):
        uwu_replacements = {
            "r": "w",
            "!": "! owo",
            "v": "w",
            "ni": "nye",
            "na": "nya",
            "ne": "nye",
            "no": "nyo",
            "nu": "nyu",
            "ove": "uv",
            "l": "w"
        }
        uwu_prefixes = ["Nya~", "Nnnnya~"]
        uwu_endings = ["OwO", "UwU", "~", "~~"]

        for key, value in uwu_replacements.items():
            message = re.sub(key, value, message, flags=re.IGNORECASE)

        if random.randint(1, 100) < 80:
            message = random.choice(uwu_prefixes) + " " + message

        if random.randint(1, 100) < 80:
            message = message + " " + random.choice(uwu_endings)

        return message

    def send_message(self, message: str, fail=False):
        if not self.discord_webhook:
            return
        if random.randint(1, 100) < 10:
            message = self.uwuizer(message)

        kwargs = {
            "url": self.discord_webhook,
            "content": message
        }

        if fail:
            kwargs["username"] = "malf-ai"
        else:
            kwargs["avatar_url"] = "https://i.redd.it/xomd902beh311.png"

        weebhook = DiscordWebhook(**kwargs)
        weebhook.execute()

    def send_normal(self, message: str):
        self.send_message(message)

    def send_error(self, message: str):
        self.send_message(message, True)

class DiscordHandler(Handler):
    def __init__(self, config: Config):
        super().__init__()
        self.discord = Discord(config)

    def emit(self, record: LogRecord) -> None:
        try:
            if record.levelno == ERROR:
                self.discord.send_error(record.getMessage())
            elif record.levelno == DEBUG:
                pass
            else:
                self.discord.send_normal(record.getMessage())
        except:
            pass