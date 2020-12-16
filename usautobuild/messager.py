import json
from discord_webhook import DiscordWebhook

from . import CONFIG


def send_success(message: str):
    if not CONFIG["discord_webhook"]:
        return
    weebhook = DiscordWebhook(
        url=CONFIG["discord_webhook"],
        content=message,
        avatar_url="https://i.redd.it/xomd902beh311.png")
    weebhook.execute()


def send_fail(message: str):
    if not CONFIG["discord_webhook"]:
        return
    message = f"ERROR: \n```\n{message}\n```"
    weebhook = DiscordWebhook(
        url=CONFIG["discord_webhook"],
        content=message,
        username="malf-ai")

    weebhook.execute()
