import shutil

from logging import getLogger
from pathlib import Path

from usautobuild.action import Action, step
from usautobuild.utils import run_process_shell

log = getLogger("usautobuild")


class Dockerizer(Action):
    @step(dry=True)
    def log_start(self) -> None:
        log.debug("Starting docker process")

    @step()
    def copy_dockerfile(self) -> None:
        log.debug("Preparing Docker folder")

        path = Path("Docker")
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree("local_repo/Docker", path)

    @step()
    def copy_server_build(self) -> None:
        log.debug("Copying server build")

        path = Path("Docker") / "server"
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree(self.config.output_dir / "linuxserver", path)

    @step()
    def make_images(self) -> None:
        log.debug("Creating images...")

        if status := run_process_shell(
            f"docker image prune -f && docker build "
            f"-t unitystation/unitystation:{self.config.build_number} "
            f"-t unitystation/unitystation:{self.config.git_branch} Docker"
        ):
            raise Exception(f"Build failed: {status}")

    @step()
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

    @step(dry=True)
    def log_done(self) -> None:
        log.info(
            "Process finished, a new staging build has been deployed and should " "shortly be present on the server."
        )
