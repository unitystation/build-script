import logging

from usautobuild.actions import ApiCaller, Builder, Dockerizer, Gitter, Licenser, Uploader
from usautobuild.cli import args
from usautobuild.config import Config
from usautobuild.logger import Logger
from usautobuild.utils import git_version

log = logging.getLogger("usautobuild")

WARNING_GIF = "https://tenor.com/view/14422456"


def main() -> None:
    with Logger(args["log_level"]) as logger:
        config = Config(args)
        logger.configure(config)

        _real_main(config)


def _real_main(config: Config) -> None:
    if args["get_license"]:
        Licenser(config).run()
        return

    log.info("Launched Build Bot version %s", git_version())

    if not config.release:
        log.warning("Running a debug build that will not be registered")
        if config.discord_webhook is not None:
            log.warning("If this is a mistake make sure to ping **PLACEHOLDER** to add --release flag %s", WARNING_GIF)

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    gitter.run()
    builder.run()
    uploader.run()
    dockerizer.run()

    if config.release:
        api_caller = ApiCaller(config)
        api_caller.run()


if __name__ == "__main__":
    main()
