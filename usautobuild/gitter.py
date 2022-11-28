from logging import getLogger
from pathlib import Path
from typing import Any

from git import RemoteProgress, Repo

from .config import Config
from .exceptions import NoChanges

log = getLogger("usautobuild")


class CloneProgress(RemoteProgress):
    def update(self, *_args: Any, message: str = "", **_kwargs: Any) -> None:
        if message:
            log.debug(message)


class Gitter:
    remote_repo: str
    local_repo: Repo
    branch: str

    def __init__(self, config: Config):
        self.config = config

    def prepare_git_directory(self) -> None:
        log.debug("Preparing git directory...")
        self.local_repo_dir = Path.cwd() / "local_repo"

        if not self.local_repo_dir.is_dir():
            self.local_repo_dir.mkdir()
            self.local_repo = self.clone_repo(self.local_repo_dir)
        else:
            self.local_repo = Repo(self.local_repo_dir)
            self.update_repo()

    def clone_repo(self, local_dir: Path) -> Repo:
        log.debug("Clonning repository...")
        return Repo.clone_from(self.remote_repo, local_dir, progress=CloneProgress())

    def update_repo(self) -> None:
        log.debug("Updating repo...")
        last_commit = self.local_repo.head.commit
        self.local_repo.remote("origin").fetch()
        self.local_repo.git.reset("--hard", f"origin/{self.config.git_branch}")
        new_commit = self.local_repo.head.commit

        if last_commit == new_commit and not self.config.allow_no_changes:
            log.error("Couldn't find changes after updating repo. Aborting build!")
            raise NoChanges(self.branch)

    def start_gitting(self) -> None:
        self.prepare_git_directory()
        self.config.project_path = self.local_repo_dir / "UnityProject"
