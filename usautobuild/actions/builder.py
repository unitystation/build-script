import json
import re
import shutil
import time

from logging import getLogger
from pathlib import Path

import humanize

from usautobuild.config import Config
from usautobuild.exceptions import (
    BuildFailedError,
    InvalidProjectPathError,
    MissingLicenseFileError
)
from usautobuild.utils import git_version, run_process_shell

exec_name = {
    "linuxserver": "Unitystation",
    "StandaloneLinux64": "Unitystation",
    "StandaloneWindows64": "Unitystation.exe",
    "StandaloneOSX": "Unitystation.app",
}

platform_image = {
    "linuxserver": "-base-3.1",
    "StandaloneLinux64": "-base-3.1",
    "StandaloneWindows64": "-windows-mono-3.1",
    "StandaloneOSX": "-mac-mono-3.1",
}

log = getLogger("usautobuild")


class Builder:
    def __init__(self, config: Config):
        self.config = config

    def check_license(self) -> None:
        log.debug("Checking license file...")
        if not self.config.license_file.exists():
            log.error("Missing license file at given directory: %s", self.config.license_file)
            raise MissingLicenseFileError(self.config.license_file)

    def clean_builds_folder(self) -> None:
        path = self.config.output_dir
        if path.is_dir():
            log.debug("Found output folder, cleaning up!")
            shutil.rmtree(path)
            path.mkdir()

    def create_builds_folders(self) -> None:
        for target in self.config.target_platforms:
            try:
                (Path.cwd() / self.config.output_dir / target).mkdir(exist_ok=True)
            except Exception as e:
                log.error("Failed to create output folders because: %s!", e)
                raise e

    def set_jsons_data(self) -> None:
        log.debug("Changing data in json files from the game...")
        if not self.config.project_path:
            log.error("Invalid path to unity project. Aborting...")
            raise InvalidProjectPathError()

        streaming_assets = self.config.project_path / "Assets" / "StreamingAssets"
        build_info = streaming_assets / "Config" / "buildinfo.json"
        config_json = streaming_assets / "Config" / "config.json"

        try:
            with build_info.open("r") as f:
                p_build_info = json.load(f)
        except FileNotFoundError:
            log.error("Couldn't find build info file!")
            raise
        try:
            with config_json.open("r") as f:
                p_config_json = json.load(f)
        except FileNotFoundError:
            log.error("Coudln't find game config file!")
            raise

        with build_info.open("w") as f:
            p_build_info["BuildNumber"] = self.config.build_number
            p_build_info["ForkName"] = self.config.forkname

            json.dump(p_build_info, f, indent=4)

        with config_json.open("w") as f:
            url = self.config.cdn_download_url
            p_config_json["WinDownload"] = url.format(
                self.config.forkname, "StandaloneWindows64", self.config.build_number
            )
            p_config_json["OSXDownload"] = url.format(self.config.forkname, "StandaloneOSX", self.config.build_number)
            p_config_json["LinuxDownload"] = url.format(
                self.config.forkname, "StandaloneLinux64", self.config.build_number
            )
            json.dump(p_config_json, f, indent=4)

    def set_addressables_mode(self) -> None:
        log.debug("Changing addressable mode from GameData.prefab...")
        prefab_file = (
            self.config.project_path / "Assets" / "Prefabs" / "SceneConstruction" / "NestedManagers" / "GameData.prefab"
        )

        try:
            with prefab_file.open(encoding="UTF-8") as f:
                prefab = f.read()
        except FileNotFoundError:
            log.error("Coudn't find GameData prefab!")
            raise FileNotFoundError()

        prefab = re.sub(r"DevBuild: \d", "DevBuild: 0", prefab)

        with prefab_file.open("w", encoding="UTF-8") as f:
            f.write(prefab)

    def make_command(self, target: str) -> str:
        image = f"unityci/editor:{self.config.unity_version}{platform_image[target]}"

        return (
            # pull first because docker run does not have -q alternative
            f"docker pull -q {image} && "
            f"docker run --rm "
            f"{self.generate_mounts()} "
            f"{image} "
            f"unity-editor "
            f"{self.generate_build_args(target)} "
            f"-logfile /root/logs/{target}.txt "
            f"-quit"
        )

    def generate_mounts(self) -> str:
        cwd = Path.cwd()

        return (
            f"-v {self.config.project_path}:/root/UnityProject "
            f"-v {self.config.output_dir}:/root/builds "
            f"-v {cwd /'logs'}:/root/logs "
            f"-v {cwd / self.config.license_file}:/root/.local/share/unity3d/Unity/Unity_lic.ulf "
        )

    def generate_build_args(self, target: str) -> str:
        return (
            f"-nographics "
            f"-ignoreCompilerErrors "
            f"-projectPath /root/UnityProject "
            f"-buildTarget {self.get_real_target(target)} "
            f"-executeMethod BuildScript.BuildProject "
            f"-customBuildPath {Path('/') / 'root' / 'builds' / target / exec_name[target]} "
            f"{self.get_devBuild_flag(target)}"
        )

    def get_real_target(self, target: str) -> str:
        if target.lower() == "linuxserver":
            return "StandaloneLinux64"

        return target

    def get_devBuild_flag(self, target: str) -> str:  # noqa: N802
        if target.lower() == "linuxserver":
            return "-devBuild -deepProfile -standaloneBuildSubtarget Server"

        return ""

    def build(self, target: str) -> None:
        command = self.make_command(target)
        log.debug("Running command\n%s\n", command)

        if run_process_shell(command):
            raise BuildFailedError(target)

    def start_building(self) -> None:
        log.info("Building version: %s", git_version(directory=self.config.project_path, brief=False))
        start = time.time()

        self.check_license()
        self.clean_builds_folder()
        self.create_builds_folders()
        self.set_jsons_data()
        self.set_addressables_mode()

        for target in self.config.target_platforms:
            log.debug("Building %s", target)

            start_target = time.time()
            try:
                self.build(target)
            except Exception as e:
                if self.config.abort_on_build_fail:
                    log.error("Abort: %s", e)
                    raise
            finally:
                log.info("%s duration: %s", target, humanize.naturaldelta(time.time() - start_target))

        log.info("Finished building in %s", humanize.naturaldelta(time.time() - start))
