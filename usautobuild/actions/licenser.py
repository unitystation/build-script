from logging import getLogger
from pathlib import Path
from subprocess import PIPE, Popen

from usautobuild.action import Action, step
from usautobuild.utils import iterate_output

log = getLogger("usautobuild")


class Licenser(Action):
    @step(dry=True)
    def log_start(self) -> None:
        log.info("Requesting a manual activation file...")

    @step(dry=True)
    def log_done(self) -> None:
        log.info("Process finished satisfactorily")

    @step()
    def prepare_licenses_folder(self) -> None:
        log.debug("Preparing licenses folder...")
        licenses_folder = Path.cwd() / "licenses"
        if not licenses_folder.is_dir():
            log.debug("Folder not found, creating it instead.")
            licenses_folder.mkdir()

    @step()
    def get_license(self) -> None:
        cwd = Path.cwd()

        command = (
            f"docker run --rm "
            f"-v {cwd / 'licenses'}:/root/licenses "
            f"-v {cwd / 'logs'}:/root/logs "
            f"-w /root/licenses "
            f"unityci/editor:{self.config.unity_version}-base-0 unity-editor "
            f"-batchmode -nographics -createManualActivationFile -logfile /root/logs/licenser.txt "
        )

        with Popen(command, stdout=PIPE, stderr=PIPE, shell=True) as cmd:
            for line, is_stdout in iterate_output(cmd):
                if is_stdout:
                    log.debug(line)
                else:
                    if "Unable to find image" not in line:
                        log.error(line)
                        raise Exception(line)
