from . import CONFIG, logger
import requests


def send_message(data):
    if not CONFIG["discord_webhook"]:
        return

    result = requests.post(CONFIG["discord_webhook"], data=data, headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.log(str(err))


def send_success(message: str):
    data = {"content": message, "username": "build-server", "avatar_url": "https://i.redd.it/xomd902beh311.png"}
    send_message(data)


def send_fail(message: str):
    message = f"ERROR: \n```\n{message}\n```"
    data = {"content": message, "username": "malf-ai"}
    send_message(data)
