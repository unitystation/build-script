import os
import json
from logging import getLogger
from pathlib import Path

from .exceptions import MissingConfigFile, InvalidConfigFile

from usautobuild.exceptions import MissingRequiredEnv

log = getLogger("usautobuild")


class Config:
    required_envs = [
        "CDN_HOST",
        "CDN_USER",
        "CDN_PASSWORD",
        "DOCKER_PASSWORD",
        "DOCKER_USERNAME",
        "CHANGELOG_API_URL",
        "CHANGELOG_API_KEY",
    ]

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

    project_path = ""
    build_number = 0

    def __init__(self, args: dict):
        self.args = args
        self.handle_config_file()
        self.handle_args()
        self.set_required_envs()

    def set_required_envs(self):
        log.info("Setting required envs...")
        for env in self.required_envs:
            value = os.environ.get(env)
            if value is None:
                log.error(f"Required env is missing: {env}")
                raise MissingRequiredEnv(env)

            setattr(self, env, value)

    def handle_config_file(self):
        if self.config_file is None:
            config_json = Path("config.json")
            if config_json.is_file():
                self.config_file = config_json

        if self.config_file is None:
            log.info("No config file found, we will proceed with all default")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            log.error(f"Missing Config file at given path: {self.config_file}")
            raise MissingConfigFile(self.config_file)
        except json.JSONDecodeError:
            log.error("JSON config file seems to be invalid!")
            raise InvalidConfigFile
        else:
            self.add_to_envs(config)

        self.set_config(config)

    def handle_args(self):
        config = {}
        for arg_var in (
            "build_number",
            "config_file",
        ):
            if arg_var in self.args:
                config[arg_var] = self.args[arg_var]

        # TODO add more args override
        self.set_config(config)

    def set_config(self, config):
        for path_var in (
            "config_file",
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

    def add_to_envs(self, config: dict):
        log.info("Adding extra keys from config file to envs...")
        for key in config.keys():
            if key in self.required_envs:
                os.environ[key] = config[key]
                log.debug(f"added {key}")
