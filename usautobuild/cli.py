import argparse

from pathlib import Path

from usautobuild.config import DEFAULT_BRANCH
from usautobuild.logger import LogLevel

__all__ = ("args",)

_default_config_path = Path("config.json")

ap = argparse.ArgumentParser(
    description="""
    Unitystation build script.
    """
)

ap.add_argument(
    "--branch",
    type=str,
    required=False,
    help=f"Git branch to use. Defaults to {DEFAULT_BRANCH}. Incompatible with --tag",
)
ap.add_argument(
    "--pr",
    type=int,
    required=False,
    help="Force a particular GitHub PR. Incompatible with --branch",
)
ap.add_argument(
    "-b",
    "--build-number",
    type=int,
    required=False,
    help="Force a particular build number",
)
ap.add_argument(
    "-L",
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
    "--release",
    action="store_true",
    help="Upload changelog and maybe do other release stuff when added",
)
ap.add_argument(
    "--dry-run",
    action="store_true",
    help="Run build until completion without uploading to FTP",
)
ap.add_argument(
    "--stable",
    action="store_true",
    help="Tag current build as stable and push to DockerHub with the stable tag",
)

args = vars(ap.parse_args())

if args["branch"] and args["pr"]:
    raise Exception("--branch conflicts with --pr")
