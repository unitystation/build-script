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
    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
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
    cdn_download_url = "https://cdn.unitystation.org/{}/{}/{}.zip"
    # First bucket is the primary (will always have the full content)
    # the rest are regional replicas that are synced from the primary
    r2_buckets = ["unitystation", "unitystation-weur", "unitystation-enam"]
    forkname = "UnityStationDevelop"

    # Build retention: keep the newest N builds per platform PLUS anything
    # younger than the age floor. 0 will disable pruning.
    prune_keep_builds = 20
    prune_min_age_days = 30

    discord_webhook: Optional[str] = None

    dry_run = False
    abort_on_build_fail = True
    allow_no_changes = True

    build_number = int(datetime.datetime.now().strftime("%y%m%d%H"))

    output_dir = Path.cwd() / "builds"
    license_file = Path.cwd() / "UnityLicense.ulf"
    project_path = Path()
