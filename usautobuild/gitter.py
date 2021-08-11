import os
from pathlib import Path
from git import Repo, RemoteProgress
from .config import  Config
from .exceptions import NoChanges
from logging import getLogger

logger = getLogger("usautobuild")

class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            logger.debug(message)

class Gitter:
    remote_repo: str
    local_repo: Repo
    branch: str

    def __init__(self, config: Config):
        self.config = config

    def prepare_git_directory(self):
        logger.debug("Preparing git directory...")
        work_dir = os.getcwd()
        self.local_repo_dir = Path(work_dir, "local_repo")

        if not os.path.isdir(self.local_repo_dir):
            os.mkdir(self.local_repo_dir)
            self.local_repo = self.clone_repo(self.local_repo_dir)
        else:
            self.local_repo = Repo(self.local_repo_dir)
            self.update_repo()

    def clone_repo(self, local_dir):
        logger.debug("Clonning repository...")
        return Repo.clone_from(self.remote_repo, local_dir, progress=CloneProgress())

    def update_repo(self):
        logger.debug("Updating repo...")
        last_commit = self.local_repo.head.commit
        self.local_repo.remote("origin").fetch()
        self.local_repo.git.reset("--hard", f"origin/{self.config.git_branch}")
        new_commit = self.local_repo.head.commit

        if last_commit == new_commit and not self.config.allow_no_changes:
            logger.error("Couldn't find changes after updating repo. Aborting build!")
            raise NoChanges(self.branch)

    def start_gitting(self):
        self.prepare_git_directory()
        self.config.project_path = Path(self.local_repo_dir, "UnityProject")

