import argparse
import logging

from pathlib import Path

from usautobuild.actions import APICaller, Builder, Dockerizer, Gitter, Licenser, Uploader
from usautobuild.config import Config
from usautobuild.logger import LogLevel, setup_extra_loggers, setup_logger, teardown_loggers
from usautobuild.utils import get_version

log = logging.getLogger("usautobuild")

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
    "-g",
    "--get-license",
    action="store_true",
    help="Get license file and quit",
)
ap.add_argument(
    "-f",
    "--config-file",
    type=Path,
    help=f"Path to the config file. Defaults to {_default_config_path}",
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
ap.add_argument(
    "-j",
    "--jobs",
    type=int,
    required=False,
    help="Defines max step concurrency. Defaults to number of CPUs x 5",
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

    log.info("Launched Build Bot version %s", get_version())

    gitter.run()
    builder.run()
    uploader.run()
    dockerizer.run()

    api_caller = APICaller(config)
    api_caller.run()


if __name__ == "__main__":
    try:
        main()
    finally:
        teardown_loggers()
