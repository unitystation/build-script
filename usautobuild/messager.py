import random
import re
from discord_webhook import DiscordWebhook

from . import CONFIG

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


def uwuizer(message: str):
    for key, value in uwu_replacements.items():
        message = re.sub(key, value, message, flags=re.IGNORECASE)

    if random.randint(1, 100) < 80:
        message = random.choice(uwu_prefixes) + " " + message

    if random.randint(1, 100) < 80:
        message = message + " " + random.choice(uwu_endings)

    return message


def send_message(message: str, fail=False):
    if not CONFIG["discord_webhook"]:
        return

    if random.randint(1, 100) < 10:
        message = uwuizer(message)

    kwargs = {
        "url": CONFIG["discord_webhook"],
        "content": message
    }

    if fail:
        kwargs["username"] = "malf-ai"
    else:
        kwargs["avatar_url"] = "https://i.redd.it/xomd902beh311.png"

    weebhook = DiscordWebhook(**kwargs)
    weebhook.execute()


def send_success(message: str):
    send_message(message)


def send_fail(message: str):
    send_message(message, fail=True)
