from logging import getLogger
from pathlib import Path
from typing import Any

from git import RemoteProgress, Repo

from usautobuild.config import Config
from usautobuild.exceptions import NoChangesError

log = getLogger("usautobuild")


class CloneProgress(RemoteProgress):
    def update(self, *_args: Any, message: str = "", **_kwargs: Any) -> None:
        if message:
            log.debug(message)


class Gitter:
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
        return Repo.clone_from(self.config.git_url, local_dir, progress=CloneProgress())  # type: ignore[arg-type]

    def update_repo(self) -> None:
        log.debug("Updating repo...")

        if self.config.github_pr_number is not None:
            branch = f"pr-{self.config.github_pr_number}"
            ref = f"pull/{self.config.github_pr_number}/head:{branch}"
        else:
            branch = f"origin/{self.config.git_branch}"
            ref = None

        last_commit = self.local_repo.head.commit
        self.local_repo.remote().fetch(ref)
        self.local_repo.git.reset("--hard", branch)
        new_commit = self.local_repo.head.commit

        if last_commit == new_commit and not self.config.allow_no_changes:
            log.error("Couldn't find changes after updating repo. Aborting build!")
            raise NoChangesError(self.config.git_branch)

    def start_gitting(self) -> None:
        self.prepare_git_directory()
        self.config.project_path = self.local_repo_dir / "UnityProject"

    def get_Good_file_tag(self) -> str:
        log.debug("Searching for the latest 'good-file-*' tag...")

        # Fetch all tags from the repository
        tags = self.local_repo.tags

        # Filter tags that start with 'good-file-'
        good_file_tags = [tag for tag in tags if tag.name.startswith("good-file-")]

        if not good_file_tags:
            raise ValueError("No 'good-file-*' tags found in the repository.")

        # Sort tags by their commit date (ascending)
        good_file_tags_sorted = sorted(
            good_file_tags,
            key=lambda tag: tag.commit.committed_datetime,
        )

        # Return the latest tag (last in the sorted list)
        latest_tag = good_file_tags_sorted[-1].name
        log.debug(f"Latest 'good-file-*' tag found: {latest_tag}")
        return latest_tag




        
