from logging import getLogger
from pathlib import Path
from subprocess import PIPE, Popen

from .config import Config
from .utils import iterate_output

log = getLogger("usautobuild")


class Licenser:
    def __init__(self, config: Config):
        self.config = config
        log.info("Requesting a manual activation file...")
        self.prepare_licenses_folder()
        self.run_command(self.make_command())
        log.info("Process finished satisfactorily")

    def prepare_licenses_folder(self) -> None:
        log.debug("Preparing licenses folder...")
        licenses_folder = Path.cwd() / "licenses"
        if not licenses_folder.is_dir():
            log.debug("Folder not found, creating it instead.")
            licenses_folder.mkdir()

    def make_command(self) -> str:
        cwd = Path.cwd()

        return (
            f"docker run --rm "
            f"-v {cwd / 'licenses'}:/root/licenses "
            f"-v {cwd / 'logs'}:/root/logs "
            f"-w /root/licenses "
            f"unityci/editor:{self.config.unity_version}-base-0 unity-editor "
            f"-batchmode -nographics -createManualActivationFile -logfile /root/logs/licenser.txt "
        )

    def run_command(self, command: str) -> None:
        log.debug(f"Running command \n{command}\n")

        with Popen(command, stdout=PIPE, stderr=PIPE, shell=True) as cmd:
            for line, is_stdout in iterate_output(cmd):
                if is_stdout:
                    if line.strip():
                        log.debug(line)
                else:
                    if line and "Unable to find image" not in line:
                        log.error(line)
                        raise Exception(line)
