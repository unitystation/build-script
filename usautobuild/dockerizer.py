import shutil

from logging import getLogger
from pathlib import Path
from subprocess import PIPE, Popen

from .config import Config

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
        try:
            cmd = Popen(
                f"docker image prune -f && docker build "
                f"-t unitystation/unitystation:{self.config.build_number} "
                f"-t unitystation/unitystation:{self.config.git_branch} Docker",
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                shell=True,
            )
            for line in cmd.stdout:
                log.debug(line)

            for line in cmd.stderr:
                raise Exception(line)

            cmd.wait()
        except Exception as e:
            log.error(str(e))
            raise e

    def push_images(self) -> None:
        log.debug("Pushing images...")
        try:
            cmd = Popen(
                f'echo "$DOCKER_PASSWORD" | ' f"docker login --username {self.config.docker_username} --password-stdin",
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                shell=True,
            )

            for line in cmd.stdout:
                log.debug(line)
            # for line in cmd.stderr:
            #     raise Exception(line)
            cmd.wait()
        except Exception as e:
            log.error(str(e))
            raise e

        try:
            cmd = Popen(
                "docker push unitystation/unitystation --all-tags",
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                shell=True,
            )
            for line in cmd.stdout:
                log.debug(line)
            # for line in cmd.stderr:
            #     raise Exception(line)
            cmd.wait()

        except Exception as e:
            log.error(str(e))
            raise e

    def start_dockering(self) -> None:
        log.debug("Starting docker process")
        self.copy_dockerfile()
        self.copy_server_build()
        self.make_images()
        self.push_images()
        log.info(
            "Process finished, a new staging build has been deployed and should " "shortly be present on the server."
        )
