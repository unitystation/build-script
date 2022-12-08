import shutil

from logging import getLogger
from pathlib import Path

from usautobuild.action import Context, step
from usautobuild.utils import run_process_shell

from .action import USAction

log = getLogger("usautobuild")


class Dockerizer(USAction):
    @step()
    def copy_dockerfile(self, _ctx: Context) -> None:
        log.debug("Preparing Docker folder")

        path = Path("Docker")
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree("local_repo/Docker", path)

    @step()
    def copy_server_build(self, _ctx: Context) -> None:
        log.debug("Copying server build")

        path = Path("Docker") / "server"
        if path.is_dir():
            shutil.rmtree(path)

        shutil.copytree(self.config.output_dir / "linuxserver", path)

    @step(depends=[copy_dockerfile, copy_server_build])
    def make_images(self, _ctx: Context) -> None:
        log.debug("Creating images...")

        if status := run_process_shell(
            f"docker image prune -f && docker build "
            f"-t unitystation/unitystation:{self.config.build_number} "
            f"-t unitystation/unitystation:{self.config.git_branch} Docker"
        ):
            raise Exception(f"Build failed: {status}")

    @step(depends=[make_images])
    def push_images(self, _ctx: Context) -> None:
        log.debug("Pushing images...")

        if status := run_process_shell(
            'echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin',
            # complains about storing credentials in filesystem
            stderr_on_failure=True,
        ):
            raise Exception(f"Docker login failed: {status}")

        if status := run_process_shell("docker push unitystation/unitystation --all-tags"):
            raise Exception(f"Docker push failed: {status}")

    def run(self) -> None:
        log.debug("Starting docker process")

        super().run()

        log.info(
            "Process finished, a new staging build has been deployed and should " "shortly be present on the server."
        )
