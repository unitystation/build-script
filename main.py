import argparse

from pathlib import Path

from usautobuild.actions import ApiCaller, Builder, Dockerizer, Gitter, Licenser, Uploader
from usautobuild.config import Config
from usautobuild.logger import LogLevel, setup_extra_loggers, setup_logger, teardown_loggers

_default_config_path = Path("config.json")

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
    help="Get license file and quit",
)
ap.add_argument(
    "-f",
    "--config-file",
    type=Path,
    help=f"Path to the config file, defaults to {_default_config_path}",
    default=_default_config_path,
)
ap.add_argument(
    "-l",
    "--log-level",
    type=LogLevel(),
    help="Logging level, defaults to info",
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
    try:
        main()
    finally:
        teardown_loggers()
