import json
import re
import shutil

from logging import getLogger
from pathlib import Path

from usautobuild.action import Action, step
from usautobuild.exceptions import BuildFailed, InvalidProjectPath, MissingLicenseFile
from usautobuild.utils import git_version, run_process_shell

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


class Builder(Action):
    @step(dry=True)
    def log_start(self) -> None:
        log.info("Starting a new build: %s", git_version(directory=self.config.project_path, brief=False))

    @step(dry=True)
    def check_license(self) -> None:
        log.debug("Checking license file...")
        if not self.config.license_file.exists():
            log.error("Missing license file at given directory: %s", self.config.license_file)
            raise MissingLicenseFile(self.config.license_file)

    @step()
    def clean_builds_folder(self) -> None:
        path = self.config.output_dir
        if path.is_dir():
            log.debug("Found output folder, cleaning up!")
            shutil.rmtree(path)
            path.mkdir()

    @step()
    def create_build_folders(self) -> None:
        for target in self.config.target_platforms:
            try:
                (Path.cwd() / self.config.output_dir / target).mkdir(exist_ok=True)
            except Exception as e:
                log.error("Failed to create output folders: %s!", e)
                raise

    @step()
    def write_build_config(self) -> None:
        log.debug("Changing data in json files from the game...")
        if not self.config.project_path:
            log.error("Invalid path to unity project. Aborting...")
            raise InvalidProjectPath()

        streaming_assets = self.config.project_path / "Assets" / "StreamingAssets"
        build_info = streaming_assets / "buildinfo.json"
        config_json = streaming_assets / "config" / "config.json"

        try:
            with open(build_info) as f:
                p_build_info = json.load(f)
        except FileNotFoundError:
            log.error("Couldn't find build info file!")
            raise
        try:
            with open(config_json) as f:
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
    def set_addressables_mode(self) -> None:
        log.debug("Changing addressable mode from GameData.prefab...")
        prefab_file = (
            self.config.project_path / "Assets" / "Prefabs" / "SceneConstruction" / "NestedManagers" / "GameData.prefab"
        )

        try:
            with open(prefab_file, encoding="UTF-8") as f:
                prefab = f.read()
        except FileNotFoundError:
            log.error("Coudn't find GameData prefab!")
            raise

        prefab = re.sub(r"DevBuild: \d", "DevBuild: 0", prefab)

        with open(prefab_file, "w", encoding="UTF-8") as f:
            f.write(prefab)

    @step()
    def build(self) -> None:
        for target in self.config.target_platforms:
            log.debug("Starting build for %s...", target)

            try:
                self.build_target(target)
            except BuildFailed:
                if self.config.abort_on_build_fail:
                    log.error("Build for %s failed and config is set to abort on fail!", target)
                    raise
            else:
                log.debug("Finished build for %s", target)

        log.info("Finished building!")

    def build_target(self, target: str) -> None:
        image = f"unityci/editor:{self.config.unity_version}{platform_image[target]}"

        cwd = Path.cwd()

        mounts = (
            f"-v {self.config.project_path}:/root/UnityProject "
            f"-v {self.config.output_dir}:/root/builds "
            f"-v {cwd /'logs'}:/root/logs "
            f"-v {cwd / self.config.license_file}:/root/.local/share/unity3d/Unity/Unity_lic.ulf "
        )

        dev_flag = " -devBuild -deepProfile" if target.lower() == "linuxserver" else ""
        target_name = "StandaloneLinux64" if target.lower() == "linuxserver" else target

        unity_args = (
            f"-nographics "
            f"-projectPath /root/UnityProject "
            f"-buildTarget {target_name} "
            f"-executeMethod BuildScript.BuildProject "
            f"-customBuildPath {Path('/') / 'root' / 'builds' / target / exec_name[target]} "
            f"{dev_flag} "
            f"-logfile /root/logs/{target}.txt "
            f"-quit"
        )

        command = (
            # pull first because docker run does not have -q alternative
            f"docker pull -q {image} && "
            f"docker run --rm {mounts} {image} unity-editor {unity_args}"
        )

        if run_process_shell(command):
            raise BuildFailed(target)
