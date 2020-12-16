import os
from datetime import datetime

report_file = os.path.join(os.getcwd(), "logs", "report.log")


def check_file():
    if not os.path.isfile(report_file):
        with open(report_file, "w", encoding="UTF-8"):
            return


def get_timestamp():
    return datetime.now()


def write_report(text: str):
    check_file()

    with open(report_file, "a", encoding="UTF-8")as f:
        if text.endswith("\n"):
            f.write(text)
        else:
            f.write(text+"\n")


def log(text: str):
    text = f"{get_timestamp()} {text}"
    print(text)
    write_report(text)
