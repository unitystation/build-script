# ruff: noqa: S311

from __future__ import annotations

import argparse
import collections
import datetime
import logging
import queue
import random
import re
import sys
import threading
import time

from logging import handlers
from pathlib import Path
from typing import Any, Optional

import requests

from .config import Config

log = logging.getLogger("usautobuild")

__all__ = (
    "Logger",
    "LogLevel",
)


class LogLevel:
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __call__(self, s: str) -> int:
        if (level := self.LEVELS.get(s.upper())) is None:
            raise argparse.ArgumentTypeError(f"Invalid logging level, expected one of {', '.join(self.LEVELS.keys())}")

        return level


class Logger:
    """Simple logger context. NOTE: it is not reusable despite being context"""

    __logger_initialized = False

    __slots__ = (
        "_level",
        "_discord_handler",
    )

    def __init__(self, level: int) -> None:
        self._level = level
        self._discord_handler: Optional[BufferedDiscordHandler] = None

    def __enter__(self) -> Logger:
        if Logger.__logger_initialized:
            raise RuntimeError("Logger can only be initialized once")

        Logger.__logger_initialized = True

        log.setLevel(self._level)

        fmt = logging.Formatter("[%(asctime)s::%(name)s::%(levelname)s] %(message)s")

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(sh)

        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)

        fh = handlers.RotatingFileHandler(
            log_path / datetime.datetime.now().strftime("%y-%m-%d-%H.log"),
            maxBytes=(1048576 * 5),
            backupCount=7,
        )
        fh.setFormatter(fmt)
        log.addHandler(fh)

        return self

    def __exit__(self, *_args: Any) -> None:
        if (discord_logger := self._discord_handler) is not None:
            discord_logger.stop()

    def configure(self, config: Config) -> None:
        """Configure complex loggers requiring config"""

        if (discord_webhook := config.discord_webhook) is not None:
            self._discord_handler = BufferedDiscordHandler(discord_webhook)
            self._discord_handler.addFilter(DiscordFilter())
            self._discord_handler.setFormatter(DicordFormatter())
            self._discord_handler.setLevel(logging.INFO)
            log.addHandler(self._discord_handler)


class DiscordFilter:
    @staticmethod
    def filter(record: logging.LogRecord) -> bool:
        if not hasattr(record, "discord"):
            return True

        return record.discord  # type: ignore[no-any-return]


class DicordFormatter(logging.Formatter):
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

    @classmethod
    def maybe_uwuize(cls, message: str) -> str:
        if random.random() < 0.9:
            return message

        for key, value in cls.uwu_replacements.items():
            message = re.sub(key, value, message, flags=re.IGNORECASE)

        if random.random() < 0.8:
            message = f"{random.choice(cls.uwu_prefixes)} {message}"

        if random.random() < 0.8:
            message = f"{message} {random.choice(cls.uwu_endings)}"

        return message

    @staticmethod
    def emojis(message: str, record: logging.LogRecord) -> str:
        custom_emoji = random.random() < 0.1

        if record.levelno >= logging.ERROR:
            if custom_emoji:
                emoji = random.choice(
                    [
                        "<:kloon:689668450250915960>",
                        "<:honk:686284698233602256>",
                        "<:malf:502254087081951242>",
                        "<:peel:686283882416570530>",
                    ],
                )
            else:
                emoji = "\N{CROSS MARK}"
        elif record.levelno >= logging.WARNING:
            if custom_emoji:
                emoji = random.choice(
                    [
                        "<:PicachuDoobly:711218115597303819>",
                        "<:doobly_drink:714016979693862973>",
                    ],
                )
            else:
                emoji = "\N{WARNING SIGN}"
        else:
            if custom_emoji:  # noqa: SIM108
                emoji = random.choice(
                    [
                        "<:ai:502254086507200524>",
                    ],
                )
            else:
                emoji = "\N{INFORMATION SOURCE}"

        return f"{emoji} {message}"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        message = self.maybe_uwuize(message)

        return self.emojis(message, record)


class BufferedDiscordHandler(logging.Handler):
    """
    Sends messages to discord webhook respecting interval and trying to group messages of the same type within buffer
    grace interval to reduce amount of requests.
    """

    # minimum time between 2 webhooks
    MIN_SEND_INTERVAL = 0.5
    # wait this long for additional messages to merge into one batch
    BUFFER_GRACE_TIME = 0.2

    DISCORD_MESSAGE_LEN_LIMIT = 2000

    def __init__(self, url: str):
        super().__init__()

        self._url = url

        self._queue: queue.SimpleQueue[Optional[logging.LogRecord]] = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._handler_loop, daemon=True)
        self._thread.start()

    def _handler_loop(self) -> None:
        # indicating magic value was consumed and we are exiting
        flushing = False

        pending_sends: collections.deque[tuple[str, bool]] = collections.deque()

        pop_timeout: Optional[float] = None
        last_pop = time.time()

        while True:
            try:
                if flushing:
                    time.sleep(pop_timeout or 0)
                else:
                    record = self._queue.get(timeout=pop_timeout)
            except queue.Empty:
                # did not get anything during buffer grace period / send interval
                if not pending_sends:
                    continue
            else:
                # magic thread exit sentinel
                if record is None:
                    if not pending_sends:
                        break

                    flushing = True
                else:
                    last_pop = time.time()
                    pending_sends.append(
                        (
                            self.format(record),
                            record.levelno >= logging.ERROR,
                        )
                    )
            finally:
                # wait forever by default
                pop_timeout = None

            message, malf = pending_sends.popleft()

            # a hatch indicating current chunk is at message length limit or next chunk has other type
            # if we do not send it we risk drowning in continuous log spam
            must_send = False

            # grab chunk of message if it exceeds message limit and put remaining part back
            if len(message) > 2000:
                must_send = True

                pending_sends.appendleft((message[self.DISCORD_MESSAGE_LEN_LIMIT :], malf))
                message = message[: self.DISCORD_MESSAGE_LEN_LIMIT]
            else:
                # try merging messages until we hit differet type or length limit
                while pending_sends:
                    next_message, next_malf = pending_sends.popleft()
                    # cannot merge because of different type or exceeded length, put back without modification
                    if next_malf != malf or len(message) + len(next_message) + 1 > self.DISCORD_MESSAGE_LEN_LIMIT:
                        must_send = True

                        pending_sends.appendleft((next_message, next_malf))
                        break

                    message = f"{message}\n{next_message}"

            # not forced to send yet and within buffer grace period -- pack things up and try one more time
            if not must_send and (remaining_buffer_grace := self.BUFFER_GRACE_TIME - (time.time() - last_pop)) > 0:
                pending_sends.appendleft((message, malf))
                pop_timeout = remaining_buffer_grace
                continue

            try:
                self.send_message(message, malf=malf)
            except Exception:
                if record is not None:
                    self.handleError(record)
                # else:
                #     pray()
            finally:
                pop_timeout = self.MIN_SEND_INTERVAL

    def send_message(self, message: str, malf: bool = False) -> bool:
        wh_data = {
            "content": message,
            # disallow any pings
            "allowed_mentions": {"parse": []},
        }

        if malf:
            wh_data["username"] = "malf-ai"
        else:
            wh_data["avatar_url"] = "https://i.redd.it/xomd902beh311.png"

        resp = requests.post(self._url, json=wh_data, timeout=10)

        return resp.status_code == 204

    def emit(self, record: logging.LogRecord) -> None:
        self._queue.put(record)

    def stop(self) -> None:
        self._queue.put(None)
        self._thread.join()
