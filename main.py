import argparse

from pathlib import Path

from usautobuild.api_caller import ApiCaller
from usautobuild.builder import Builder
from usautobuild.config import Config
from usautobuild.dockerizer import Dockerizer
from usautobuild.gitter import Gitter
from usautobuild.licenser import Licenser
from usautobuild.logger import LogLevel, setup_extra_loggers, setup_logger
from usautobuild.uploader import Uploader

ap = argparse.ArgumentParser()
ap.add_argument(
    "-b",
    "--build-number",
    type=int,
    required=False,
    help="Force a particular build number",
)
ap.add_argument(
    "-gl",
    "--get-license",
    action="store_true",
    help="If set to true, it will ignore all other procedure and just create a license file",
)
ap.add_argument(
    "-f",
    "--config-file",
    type=Path,
    help="Path to the config file",
    default=Path("config.json"),
)
ap.add_argument(
    "-l",
    "--log-level",
    type=LogLevel(),
    help="Log level to run this program",
    default="INFO",
)
ap.add_argument(
    "--dry-run",
    action="store_true",
    help="Run build until completion without uploading to FTP",
)
args = vars(ap.parse_args())


def main() -> None:
    setup_logger(args["log_level"])

    config = Config(args)
    setup_extra_loggers(config)

    if args["get_license"]:
        Licenser(config)
        return

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    api_caller = ApiCaller(config)
    api_caller.post_new_version()


if __name__ == "__main__":
    main()
