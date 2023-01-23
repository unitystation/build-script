import logging

from usautobuild.actions import ApiCaller, Builder, Dockerizer, Gitter, Licenser, Uploader
from usautobuild.cli import args
from usautobuild.config import Config
from usautobuild.logger import setup_extra_loggers, setup_logger, teardown_loggers
from usautobuild.utils import git_version

log = logging.getLogger("usautobuild")

WARNING_GIF = "https://tenor.com/view/warning-you-gif-14422456"


def main() -> None:
    setup_logger(args["log_level"])

    config = Config(args)
    setup_extra_loggers(config)

    if args["get_license"]:
        Licenser(config)
        return

    if not config.release:
        log.warning("running a debug build that will not be registered")
        log.warning(f"if this is a mistake make sure to ping whoever started it to add --release flag {WARNING_GIF}")

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    log.info("Launched Build Bot version %s", git_version())

    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    if config.release:
        api_caller = ApiCaller(config)
        api_caller.post_new_version()


if __name__ == "__main__":
    try:
        main()
    finally:
        teardown_loggers()
