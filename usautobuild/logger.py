import logging
from logging import handlers
import datetime
import sys

def setup_logger(arg_level: str):

    log = logging.getLogger('usautobuild')
    log.setLevel(get_log_level(arg_level))

    format = logging.Formatter("[%(asctime)s::%(name)s::%(levelname)s] %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(format)
    log.addHandler(ch)

    fh = handlers.RotatingFileHandler(
        f"logs/{datetime.datetime.now().strftime('%y-%m-%d-%H.log')}",
        maxBytes=(1048576 * 5),
        backupCount=7)
    fh.setFormatter(format)
    log.addHandler(fh)

def get_log_level(arg_level: str):
    if arg_level:
        if arg_level.upper() == "DEBUG":
            log_level = logging.DEBUG
        elif arg_level.upper() == "INFO":
            log_level = logging.INFO
        elif arg_level.upper() == "WARNING":
            log_level = logging.WARNING
        elif arg_level.upper() == "ERROR":
            log_level = logging.ERROR
        else:
            log_level = logging.INFO
    else:
        log_level = logging.INFO
    return log_level

