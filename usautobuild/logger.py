import datetime
import sys
import random
import re
import logging
from logging import handlers
from pathlib import Path

import requests

from .config import Config

log = logging.getLogger("usautobuild")


def str_to_log_level(s: str) -> int:
    level_name_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    return level_name_map.get(s.upper(), logging.INFO)


def setup_logger(arg_level: str):
    """Configure basic logging facilities"""

    log.setLevel(str_to_log_level(arg_level))

    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)

    fmt = logging.Formatter("[%(asctime)s::%(name)s::%(levelname)s] %(message)s")

    for handler in (
        logging.StreamHandler(sys.stdout),
        handlers.RotatingFileHandler(
            log_path / datetime.datetime.now().strftime("%y-%m-%d-%H.log"),
            maxBytes=(1048576 * 5),
            backupCount=7,
        ),
    ):
        handler.setFormatter(fmt)
        log.addHandler(handler)


def setup_extra_loggers(config: Config):
    """Configure complex loggers requiring config"""

    discord_webhook = config.discord_webhook
    if discord_webhook is not None:
        handler = DiscordHandler(discord_webhook)
        handler.setLevel(logging.INFO)
        log.addHandler(handler)


class DiscordHandler(logging.Handler):
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
        "l": "w",
    }
    uwu_prefixes = (
        "Nya~",
        "Nnnnya~",
    )
    uwu_endings = (
        "OwO",
        "UwU",
        "~",
        "~~",
    )

    def __init__(self, url: str):
        super().__init__()

        self.url = url

    @classmethod
    def uwuize(cls, message: str) -> str:
        for key, value in cls.uwu_replacements.items():
            message = re.sub(key, value, message, flags=re.IGNORECASE)

        if random.random() < .8:
            message = f"{random.choice(cls.uwu_prefixes)} {message}"

        if random.random() < .8:
            message = f"{message} {random.choice(cls.uwu_endings)}"

        return message

    def send_message(self, message: str, fail: bool = False) -> bool:
        if random.random() < .1:
            message = self.uwuize(message)

        wh_data = {
            "content": message,
            # disallow any pings
            "allowed_mentions": {"parse": []},
        }

        if fail:
            wh_data["username"] = "malf-ai"
        else:
            wh_data["avatar_url"] = "https://i.redd.it/xomd902beh311.png"

        resp = requests.post(self.url, json=wh_data)

        return resp.status_code == 204

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.send_message(
                record.getMessage(),
                fail=record.levelno >= logging.ERROR,
            )
        except Exception:
            self.handleError(record)
