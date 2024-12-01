import logging

from usautobuild.actions import (
    ApiCaller,
    Builder,
    DiscordChangelogPoster,
    Dockerizer,
    Gitter,
    Licenser,
    Uploader,
    tag_as_stable,
    good_files
)
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

    if args["stable"]:
        tag_as_stable()
        return

    log.info("Launched Build Bot version %s", git_version())

    if not config.release:
        log.warning("Running a debug build that will not be registered")
        log.warning("If this is a mistake make sure to ping whoever started it to add --release flag %s", WARNING_GIF)

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    do_good_files = good_files(config)

    gitter.start_gitting()

    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    if (config.do_good_files):
        tag = gitter.get_Good_file_tag().replace("good-file-", "")
        if not uploader.check_good_file_version_folder_exists(tag):
            do_good_files.make_good_files_build(tag)
            uploader.Zip_And_Upload_Good_files(tag)

    if config.release:
        api_caller = ApiCaller(config)
        api_caller.post_new_version()
        changelog_poster = DiscordChangelogPoster(config)
        changelog_poster.start_posting()


if __name__ == "__main__":
    main()
