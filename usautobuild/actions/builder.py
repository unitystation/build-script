import json
import re
import shutil

from logging import getLogger
from pathlib import Path

from usautobuild.action import Context, step
from usautobuild.exceptions import BuildFailed, InvalidProjectPath, MissingLicenseFile
from usautobuild.utils import run_process_shell

from .action import USAction

exec_name = {
    "linuxserver": "Unitystation",
    "StandaloneLinux64": "Unitystation",
    "StandaloneWindows64": "Unitystation.exe",
    "StandaloneOSX": "Unitystation.app",
}

platform_image = {
    "linuxserver": "-base-1",
    "StandaloneLinux64": "-base-1",
    "StandaloneWindows64": "-windows-mono-1",
    "StandaloneOSX": "-mac-mono-1",
}

log = getLogger("usautobuild")


class Builder(USAction):
    @step(dry=True)
    def check_license(self, _ctx: Context) -> None:
        log.debug("Checking license file...")
        if not self.config.license_file.exists():
            log.error(f"Missing license file at given directory: {self.config.license_file}")
            raise MissingLicenseFile(self.config.license_file)

    @step()
    def clean_builds_folder(self, _ctx: Context) -> None:
        path = self.config.output_dir
        if path.is_dir():
            log.debug("Found output folder, cleaning up!")
            shutil.rmtree(path)
            path.mkdir()

    @step(depends=[clean_builds_folder])
    def create_builds_folders(self, _ctx: Context) -> None:
        for target in self.config.target_platforms:
            try:
                (Path.cwd() / self.config.output_dir / target).mkdir(exist_ok=True)
            except Exception as e:
                log.error(f"Failed to create output folders because: {e}!")
                raise e

    @step()
    def set_jsons_data(self, _ctx: Context) -> None:
        log.debug("Changing data in json files from the game...")
        if not self.config.project_path:
            log.error("Invalid path to unity project. Aborting...")
            raise InvalidProjectPath()

        streaming_assets = Path(self.config.project_path, "Assets", "StreamingAssets")
        build_info = Path(streaming_assets, "buildinfo.json")
        config_json = Path(streaming_assets, "config", "config.json")

        try:
            with open(build_info, "r") as f:
                p_build_info = json.load(f)
        except FileNotFoundError:
            log.error("Couldn't find build info file!")
            raise
        try:
            with open(config_json, "r") as f:
                p_config_json = json.load(f)
        except FileNotFoundError:
            log.error("Coudln't find game config file!")
            raise

        with open(build_info, "w") as f:
            p_build_info["BuildNumber"] = self.config.build_number
            p_build_info["ForkName"] = self.config.forkname

            json.dump(p_build_info, f, indent=4)

        with open(config_json, "w") as f:
            url = self.config.cdn_download_url
            p_config_json["WinDownload"] = url.format(
                self.config.forkname, "StandaloneWindows64", self.config.build_number
            )
            p_config_json["OSXDownload"] = url.format(self.config.forkname, "StandaloneOSX", self.config.build_number)
            p_config_json["LinuxDownload"] = url.format(
                self.config.forkname, "StandaloneLinux64", self.config.build_number
            )
            json.dump(p_config_json, f, indent=4)

    @step()
    def set_addressables_mode(self, _ctx: Context) -> None:
        log.debug("Changing addressable mode from GameData.prefab...")
        file = Path(
            self.config.project_path, "Assets", "Prefabs", "SceneConstruction", "NestedManagers", "GameData.prefab"
        )

        try:
            with open(file, "r", encoding="UTF-8") as f:
                file_content = f.read()
        except FileNotFoundError:
            log.error("Coudn't find GameData prefab!")
            raise FileNotFoundError()

        file_content = re.sub(r"DevBuild: \d", "DevBuild: 0", file_content)

        with open(file, "w", encoding="UTF-8") as f:
            f.write(file_content)

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
            f"-projectPath /root/UnityProject "
            f"-buildTarget {self.get_real_target(target)} "
            f"-executeMethod BuildScript.BuildProject "
            f"-customBuildPath {Path('/root', 'builds', target, exec_name[target])} "
            f"{self.get_devBuild_flag(target)}"
        )

    def get_real_target(self, target: str) -> str:
        if target.lower() == "linuxserver":
            return "StandaloneLinux64"

        return target

    def get_devBuild_flag(self, target: str) -> str:
        if target.lower() == "linuxserver":
            return "-devBuild -deepProfile"

        return ""

    def build(self, target: str) -> None:
        command = self.make_command(target)
        log.debug(f"Running command\n{command}\n")

        if run_process_shell(command):
            raise BuildFailed(target)

    @step(depends=[check_license, create_builds_folders, set_jsons_data, set_addressables_mode])
    def start_building(self, _ctx: Context) -> None:
        for target in self.config.target_platforms:
            log.debug(f"Starting build for {target}...")

            try:
                self.build(target)
            except BuildFailed:
                if self.config.abort_on_build_fail:
                    log.error(f"Build for {target} failed and config is set to abort on fail!")
                    raise
            else:
                log.debug(f"Finished build for {target}")

    def run(self) -> None:
        log.info("Starting a new build!")

        super().run()

        log.info("Finished building!")
