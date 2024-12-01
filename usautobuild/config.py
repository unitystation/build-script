# ruff: noqa: RUF012

import datetime

from pathlib import Path
from typing import Optional

from .config_base import ConfigBase, Var

__all__ = ("Config", "DEFAULT_BRANCH")

DEFAULT_BRANCH = "develop"


class Config(ConfigBase):
    release: bool = False
    do_good_files : bool
    cdn_host: str
    cdn_user: str
    cdn_password: str
    docker_password: str
    docker_username: str
    changelog_api_url: str
    changelog_api_key: str
    changelog_webhook: str
    newest_build_api_url: str

    git_url = "https://github.com/unitystation/unitystation.git"
    git_branch = Var(DEFAULT_BRANCH, arg="branch")
    github_pr_number: Optional[int] = Var(None, arg="pr")

    unity_version = "2020.1.17f1"
    target_platforms = ["linuxserver", "StandaloneWindows64", "StandaloneOSX", "StandaloneLinux64"]
    cdn_download_url = "https://unitystationfile.b-cdn.net/{}/{}/{}.zip"
    forkname = "UnityStationDevelop"

    discord_webhook: Optional[str] = None

    dry_run = False
    abort_on_build_fail = True
    allow_no_changes = True

    build_number = int(datetime.datetime.now().strftime("%y%m%d%H"))

    output_dir = Path.cwd() / "builds"
    license_file = Path.cwd() / "UnityLicense.ulf"
    project_path = Path()
