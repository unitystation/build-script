import logging

from usautobuild.actions import ApiCaller, Builder, Dockerizer, Gitter, Licenser, Uploader, DiscordChangelogPoster, tag_as_stable
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
        Licenser(config)
        return

    if args["tag_as_stable"]:
        tag_as_stable()
        return

    log.info("Launched Build Bot version %s", git_version())

    if not config.release:
        log.warning("Running a debug build that will not be registered")
        log.warning(f"If this is a mistake make sure to ping whoever started it to add --release flag {WARNING_GIF}")

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    if config.release:
        api_caller = ApiCaller(config)
        api_caller.post_new_version()
        changelog_poster = DiscordChangelogPoster(config)
        changelog_poster.start_posting()


if __name__ == "__main__":
    main()
