from .config import Config
from logging import getLogger
from pathlib import Path
import os
from subprocess import Popen, PIPE

logger = getLogger("usautobuild")

class Licenser:
    def __init__(self, config: Config):
        self.config = config
        logger.info("Requesting a manual activation file...")
        self.prepare_licenses_folder()
        self.run_command(self.make_command())
        logger.info("Process finished satisfactorily")

    def prepare_licenses_folder(self):
        logger.debug("Preparing licenses folder...")
        licenses_folder = Path(os.getcwd(), "licenses")
        if not os.path.isdir(licenses_folder):
            logger.debug("Folder not found, creating it instead.")
            os.mkdir(licenses_folder)

    def make_command(self):
        return \
            f"docker run --rm " \
            f"-v {Path(os.getcwd(), 'licenses')}:/root/licenses " \
            f"-v {Path(os.getcwd(), 'logs')}:/root/logs " \
            f"-w /root/licenses " \
            f"unityci/editor:{self.config.unity_version}-base-0 unity-editor " \
            f"-batchmode -nographics -createManualActivationFile -logfile /root/logs/licenser.txt "

    def run_command(self, command: str):
        logger.debug(f"Running command \n{command}\n")
        cmd = Popen(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)

        for line in cmd.stdout:
            if line.strip():
                logger.debug(line)
        for line in cmd.stderr:
            if line and not "Unable to find image" in line:
                logger.error(line)
                raise Exception(line)

