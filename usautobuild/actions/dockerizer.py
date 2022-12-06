import shutil

from logging import getLogger
from pathlib import Path

from usautobuild.config import Config
from usautobuild.utils import run_process_shell

log = getLogger("usautobuild")


class Dockerizer:
    def __init__(self, config: Config):
        self.config = config

    def copy_dockerfile(self) -> None:
        log.debug("Preparing Docker folder")

        path = Path("Docker")
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree("local_repo/Docker", path)

    def copy_server_build(self) -> None:
        log.debug("Copying server build")

        path = Path("Docker") / "server"
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree(self.config.output_dir / "linuxserver", path)

    def make_images(self) -> None:
        log.debug("Creating images...")

        if status := run_process_shell(
            f"docker image prune -f && docker build "
            f"-t unitystation/unitystation:{self.config.build_number} "
            f"-t unitystation/unitystation:{self.config.git_branch} Docker"
        ):
            raise Exception(f"Build failed: {status}")

    def push_images(self) -> None:
        log.debug("Pushing images...")

        if status := run_process_shell(
            'echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin',
            # complains about storing credentials in filesystem
            stderr_on_failure=True,
        ):
            raise Exception(f"Docker login failed: {status}")

        if status := run_process_shell("docker push unitystation/unitystation --all-tags"):
            raise Exception(f"Docker push failed: {status}")

    def start_dockering(self) -> None:
        if self.config.dry_run:
            log.info("Dry run, skipping dockerization")
            return
        log.debug("Starting docker process")
        self.copy_dockerfile()
        self.copy_server_build()
        self.make_images()
        self.push_images()
        log.info(
            "Process finished, a new staging build has been deployed and should " "shortly be present on the server."
        )
