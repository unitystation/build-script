from pathlib import Path
from typing import Optional

from .config_base import ConfigBase

__all__ = ("Config",)


class Config(ConfigBase):
    cdn_host: str
    cdn_user: str
    cdn_password: str
    docker_password: str
    docker_username: str
    changelog_api_url: str
    changelog_api_key: str

    git_url = "https://github.com/unitystation/unitystation.git"
    git_branch = "develop"

    unity_version = "2020.1.17f1"
    target_platforms = ["linuxserver", "StandaloneWindows64", "StandaloneOSX", "StandaloneLinux64"]
    cdn_download_url = "https://unitystationfile.b-cdn.net/{}/{}/{}.zip"
    forkname = "UnityStationDevelop"

    discord_webhook: Optional[str] = None

    dry_run = False
    abort_on_build_fail = True
    allow_no_changes = True

    build_number: Optional[int] = None

    output_dir = Path.cwd() / "builds"
    license_file = Path.cwd() / "UnityLicense.ulf"
    project_path = Path()
