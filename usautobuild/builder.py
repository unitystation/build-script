import json
import os
import re
import shutil
from pathlib import Path
from subprocess import Popen, PIPE

from logging import getLogger
from .config import Config
from .exceptions import InvalidProjectPath, BuildFailed, MissingLicenseFile
import datetime

exec_name = {
    "linuxserver": "Unitystation",
    "StandaloneLinux64": "Unitystation",
    "StandaloneWindows64": "Unitystation.exe",
    "StandaloneOSX": "Unitystation.app"
}

platform_image = {
    "linuxserver": "-base-0",
    "StandaloneLinux64": "-base-0",
    "StandaloneWindows64": "-windows-mono-0",
    "StandaloneOSX": "-mac-mono-0"
}

logger = getLogger("usautobuild")


class Builder:
    def __init__(self, config: Config):
        self.config = config

    def produce_build_number(self):
        logger.debug("Producing build number...")
        self.config.build_number = datetime.datetime.now().strftime("%y%m%d%H")

    def load_license(self):
        logger.debug("Loading license file...")
        try:
            with open(self.config.license_file, 'r') as f:
                os.environ["UNITY_LICENSE"] = f.read()
        except FileNotFoundError:
            logger.error(f"Missing license file at given directory: {self.config.license_file}")
            raise MissingLicenseFile(self.config.license_file)

    def clean_builds_folder(self):
        if os.path.isdir(self.config.output_dir):
            logger.debug("Found output folder, cleaning up!")
            shutil.rmtree(self.config.output_dir)
            os.mkdir(self.config.output_dir)

    def create_builds_folders(self):
        for target in self.config.target_platforms:
            try:
                os.makedirs(Path(os.getcwd(), self.config.output_dir, target), exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create output folders because: {str(e)}!")
                raise e

    def set_jsons_data(self):
        logger.debug("Changing data in json files from the game...")
        if not self.config.project_path:
            logger.error("Invalid path to unity project. Aborting...")
            raise InvalidProjectPath()

        streaming_assets = Path(self.config.project_path, "Assets", "StreamingAssets")
        build_info = Path(streaming_assets, "buildinfo.json")
        config_json = Path(streaming_assets, "config", "config.json")

        try:
            with open(build_info, 'r') as f:
                p_build_info = json.load(f)
        except FileNotFoundError:
            logger.error("Couldn't find build info file!")
            raise FileNotFoundError()
        try:
            with open(config_json, 'r') as f:
                p_config_json = json.load(f)
        except FileNotFoundError:
            logger.error("Coudln't find game config file!")
            raise FileNotFoundError()

        with open(build_info, 'w') as f:
            p_build_info["BuildNumber"] = self.config.build_number
            p_build_info["ForkName"] = self.config.forkname

            json.dump(p_build_info, f, indent=4)

        with open(config_json, 'w') as f:
            url = self.config.cdn_download_url
            p_config_json["WinDownload"] = url.format(self.config.forkname, "StandaloneWindows64",
                                                      self.config.build_number)
            p_config_json["OSXDownload"] = url.format(self.config.forkname, "StandaloneOSX",
                                                      self.config.build_number)
            p_config_json["LinuxDownload"] = url.format(self.config.forkname, "StandaloneLinux64",
                                                        self.config.build_number)
            json.dump(p_config_json, f, indent=4)

    def set_addressables_mode(self):
        logger.debug("Changing addressable mode from GameData.prefab...")
        file = Path(self.config.project_path, "Assets", "Prefabs", "SceneConstruction", "NestedManagers",
                    "GameData.prefab")

        try:
            with open(file, "r", encoding="UTF-8") as f:
                file_content = f.read()
        except FileNotFoundError:
            logger.error("Coudn't find GameData prefab!")
            raise FileNotFoundError()

        file_content = re.sub(r"DevBuild: \d", f"DevBuild: 0", file_content)

        with open(file, "w", encoding="UTF-8") as f:
            f.write(file_content)

    def make_command(self, target: str):
        return \
            f"docker run --rm " \
            f"{self.generate_mounts()} " \
            f"unityci/editor:{self.config.unity_version}{platform_image[target]} " \
            f"unity-editor " \
            f"{self.generate_build_args(target)} " \
            f"-logfile /root/logs/{target}.txt " \
            f"-quit"

    def generate_mounts(self):
        return \
            f"-v {self.config.project_path}:/root/UnityProject " \
            f"-v {self.config.output_dir}:/root/builds " \
            f"-v {Path(os.getcwd(), 'logs')}:/root/logs " \
            f"-v {Path(os.getcwd(), self.config.license_file)}:/root/.local/share/unity3d/Unity/Unity_lic.ulf "

    def generate_build_args(self, target):
        return \
            f"-nographics " \
            f"-projectPath /root/UnityProject " \
            f"-buildTarget {self.get_real_target(target)} " \
            f"-executeMethod BuildScript.BuildProject " \
            f"-customBuildPath {Path('/root', 'builds', exec_name[target])} " \
            f"{self.get_devBuild_flag(target)}"

    def get_real_target(self, target: str):
        if target.lower() == "linuxserver":
            return "StandaloneLinux64"

        return target

    def get_devBuild_flag(self, target: str):
        if target.lower() == "linuxserver":
            return "-devBuild -deepProfile"

        return ""

    def build(self, target):
        command = self.make_command(target)
        logger.debug(f"Running command\n{command}\n")
        build_finished = False
        cmd = Popen(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)

        for line in cmd.stdout:
            if line.strip():
                logger.debug(line)
            if "Build succeeded!" in line:  # This is an awful way to check it, but Unity sucks dicks
                build_finished = True

        for line in cmd.stderr:
            if line and "Unable to find image" not in line:
                logger.error(line)
                raise BuildFailed(target)

        cmd.wait()
        # if not build_finished:
        #     raise BuildFailed(target)

    def start_building(self):
        logger.info("Starting a new build!")

        self.produce_build_number()
        self.load_license()
        self.clean_builds_folder()
        self.create_builds_folders()
        self.set_jsons_data()
        self.set_addressables_mode()

        for target in self.config.target_platforms:
            logger.debug(f"Starting build for {target}...")

            try:
                self.build(target)
            except BuildFailed:
                if self.config.abort_on_build_fail:
                    logger.error(f"Build for {target} failed and config is set to abort on fail!")
                    raise BuildFailed(target)
            else:
                logger.debug(f"Finished build for {target}")

        logger.info("Finished building!")
