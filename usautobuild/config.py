import os
import json
from logging import getLogger
from pathlib import Path

from .exceptions import MissingConfigFile, InvalidConfigFile

from usautobuild.exceptions import MissingRequiredEnv

logger = getLogger("usautobuild")


class Config:
    required_envs = [
        "CDN_HOST",
        "CDN_USER",
        "CDN_PASSWORD",
        "DOCKER_PASSWORD",
        "DOCKER_USERNAME"]
    config_file = None
    git_url = "https://github.com/unitystation/unitystation.git"
    git_branch = "develop"
    allow_no_changes = True
    unity_version = "2020.1.17f1"
    target_platforms = ["linuxserver", "StandaloneWindows64", "StandaloneOSX", "StandaloneLinux64"]
    cdn_download_url = "https://unitystationfile.b-cdn.net/{}/{}/{}.zip"
    forkname = "UnityStationDevelop"
    output_dir = Path(os.getcwd(), 'builds')
    license_file = Path(os.getcwd(), "UnityLicense.ulf")
    discord_webhook = ""
    abort_on_build_fail = True

    project_path = ""
    build_number = 0

    def __init__(self, config_file: str = None):
        if config_file:
            self.config_file = config_file
        self.parse_config_file()
        self.check_required_envs()
        self.get_required_envs()

    def check_required_envs(self):
        logger.info("Checking required envs...")
        for env in self.required_envs:
            i = os.getenv(env)
            if i is None:
                logger.error(f"Required env is missing: {env}")
                raise MissingRequiredEnv(env)

    def get_required_envs(self):
        self.cdn_host = os.getenv("CDN_HOST")
        self.cdn_user = os.getenv("CDN_USER")
        self.cdn_password = os.getenv("CDN_PASSWORD")
        self.docker_password = os.getenv("DOCKER_PASSWORD")
        self.docker_username = os.getenv("DOCKER_USERNAME")

    def parse_config_file(self):
        if not self.config_file and os.path.isfile("config.json"):
            self.config_file = "config.json"
        if not self.config_file:
            logger.info("No config file found, we will proceed with all default")
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Missing Config file at given path: {self.config_file}")
            raise MissingConfigFile(self.config_file)
        except json.JSONDecodeError or TypeError:
            logger.error("JSON config file seems to be invalid!")
            raise InvalidConfigFile
        else:
            self.add_to_envs(config)

        if config.get("build_number"):
            self.build_number = config.get("build_number")
        if config.get("git_url"):
            self.git_url = config.get("git_url")
        if config.get("git_branch"):
            self.git_branch = config.get("git_branch")
        if config.get("unity_version"):
            self.unity_version = config.get("unity_version")
        if config.get("target_platforms"):
            self.target_platforms = config.get("target_platforms")
        if config.get("cdn_download_url"):
            self.cdn_download_url = config.get("cdn_download_url")
        if config.get("forkname"):
            self.forkname = config.get("forkname")
        if config.get("output_dir"):
            self.output_dir = config.get("output_dir")
        if config.get("license_file"):
            self.license_file = config.get("license_file")
        if config.get("abort_build_on_fail"):
            self.abort_on_build_fail = config.get("abort_build_on_fail")
        if config.get("discord_webhook"):
            self.discord_webhook = config.get("discord_webhook")
        if config.get("allow_new_changes"):
            self.allow_no_changes = config.get("allow_new_changes")
        if config.get("abort_on_build_fail"):
            self.abort_on_build_fail = config.get("abort_on_build_fail")

    def add_to_envs(self, config: dict):
        logger.info("Adding extra keys from config file to envs...")
        for key in config.keys():
            if key not in ["build_number", "git_url", "git_branch", "allow_no_changes",
                           "unity_version", "target_platforms", "cdn_download_url",
                           "forkname", "output_dir", "discord_webhook", "license_file"]:
                os.environ[key] = config[key]
                logger.debug(f"added {key}")
