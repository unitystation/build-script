import json
import os

from logging import getLogger
from pathlib import Path
from typing import Any, Optional

from usautobuild.exceptions import MissingRequiredEnv

from .exceptions import InvalidConfigFile, MissingConfigFile

log = getLogger("usautobuild")


class Config:
    envs_to_config_map = {
        "CDN_HOST": "cdn_host",
        "CDN_USER": "cdn_user",
        "CDN_PASSWORD": "cdn_password",
        "DOCKER_PASSWORD": "docker_password",
        "DOCKER_USERNAME": "docker_username",
        "CHANGELOG_API_URL": "changelog_api_url",
        "CHANGELOG_API_KEY": "changelog_api_key",
    }
    config_to_envs_map = {v: k for k, v in envs_to_config_map.items()}

    cdn_host: str
    cdn_user: str
    cdn_password: str
    docker_password: str
    docker_username: str
    changelog_api_url: str
    changelog_api_key: str

    config_file = None
    git_url = "https://github.com/unitystation/unitystation.git"
    git_branch = "develop"
    allow_no_changes = True
    unity_version = "2020.1.17f1"
    target_platforms = ["linuxserver", "StandaloneWindows64", "StandaloneOSX", "StandaloneLinux64"]
    cdn_download_url = "https://unitystationfile.b-cdn.net/{}/{}/{}.zip"
    forkname = "UnityStationDevelop"
    output_dir = Path.cwd() / "builds"
    license_file = Path.cwd() / "UnityLicense.ulf"
    discord_webhook = ""
    abort_on_build_fail = True

    project_path = Path()
    build_number = 0

    def __init__(self, args: dict[str, Any], config_file: Optional[str] = None):
        self.args = args
        if config_file:
            self.config_file = Path(config_file)
        self.handle_config_file()
        self.handle_args()
        self.set_required_envs()

    def set_required_envs(self) -> None:
        log.info("Setting required envs...")
        for env_key, config_key in self.envs_to_config_map.items():
            value = os.environ.get(env_key)
            if value is None:
                log.error(f"Required env is missing: {env_key}")
                raise MissingRequiredEnv(env_key)

            setattr(self, config_key, value)

    def handle_config_file(self) -> None:
        if self.config_file is None:
            config_json = Path("config.json")
            if config_json.is_file():
                self.config_file = config_json

        if self.config_file is None:
            log.info("No config file found, we will proceed with all default")
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            log.error(f"Missing Config file at given path: {self.config_file}")
            raise MissingConfigFile(self.config_file)
        except json.JSONDecodeError:
            log.error("JSON config file seems to be invalid!")
            raise InvalidConfigFile

        self.add_to_envs(config)
        self.set_config(config)

    def handle_args(self) -> None:
        config = {}
        if self.args.get("build_number"):
            config["build_number"] = self.args.get("build_number")
        # TODO add more args override
        self.set_config(config)

    def set_config(self, config: dict[str, Any]) -> None:
        for path_var in (
            "output_dir",
            "license_file",
        ):
            if path_var in config:
                setattr(self, path_var, Path(config[path_var]))

        for var in (
            "build_number",
            "git_url",
            "git_branch",
            "unity_version",
            "target_platforms",
            "cdn_download_url",
            "forkname",
            "discord_webhook",
            "allow_new_changes",
            "abort_on_build_fail",
        ):
            if var in config:
                setattr(self, var, config[var])

    def add_to_envs(self, config: dict[str, Any]) -> None:
        log.info("Adding extra keys from config file to envs...")
        for config_key, value in config.items():
            if (env_key := self.config_to_envs_map.get(config_key)) is not None:
                os.environ[env_key] = value
                log.debug(f"added {env_key}")
