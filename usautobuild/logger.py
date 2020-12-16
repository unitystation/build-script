import os
from datetime import datetime


def check_file():
    if not os.path.isfile("report.log"):
        with open("report.log", "w", encoding="UTF-8"):
            return


def get_timestamp():
    return datetime.now()


def write_report(text: str):
    check_file()

    with open("report.log", "a", encoding="UTF-8")as f:
        if text.endswith("\n"):
            f.write(text)
        else:
            f.write(text+"\n")


def log(text: str):
    text = f"{get_timestamp()} {text}"
    print(text)
    write_report(text)
