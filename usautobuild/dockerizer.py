from .config import Config
from logging import getLogger
from subprocess import Popen, PIPE
import os
import shutil
from pathlib import Path

logger = getLogger("usautobuild")

class Dockerizer:
    def __init__(self, config: Config):
        self.output_dir = config.output_dir
        self.username = config.docker_username
        self.password = config.docker_password
        self.forkname = config.forkname
        self.build_number = config.build_number

    def copy_dockerfile(self):
        logger.debug("Preparing Docker folder")
        if os.path.isdir("Docker"):
            shutil.rmtree("Docker")
        shutil.copytree("local_repo/Docker", "Docker")

    def copy_server_build(self):
        logger.debug("Copying server build")
        if os.path.isdir("Docker/server"):
            shutil.rmtree("Docker/server")

        shutil.copytree(Path(self.output_dir, "linuxserver"), "Docker/server")

    def make_images(self):
        logger.debug("Creating images...")
        try:
            cmd = Popen(f"docker build "
                        f"-t unitystation/unitystation:{self.build_number} "
                        f"-t unitystation/unitystation:{self.forkname}_latest Docker",
                        stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            for line in cmd.stdout:
                logger.debug(line)

            for line in cmd.stderr:
                raise Exception(line)

            cmd.wait()
        except Exception as e:
            logger.error(str(e))
            raise e

    def push_images(self):
        logger.debug("Pushing images...")
        try:
            cmd = Popen(f'echo "$DOCKER_PASSWORD" | docker login --username {self.username} --password-stdin',
                        stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)

            for line in cmd.stdout:
                logger.debug(line)
            # for line in cmd.stderr:
            #     raise Exception(line)
            cmd.wait()
        except Exception as e:
            logger.error(str(e))
            raise e

        try:
            cmd = Popen("docker push unitystation/unitystation --all-tags",
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True,
                        shell=True)
            for line in cmd.stdout:
                logger.debug(line)
            # for line in cmd.stderr:
            #     raise Exception(line)
            cmd.wait()

        except Exception as e:
            logger.error(str(e))
            raise e

    def start_dockering(self):
        logger.debug("Starting docker process")
        self.copy_dockerfile()
        self.copy_server_build()
        self.make_images()
        self.push_images()
        logger.info("Process finished, a new staging build has been deployed and should shortly be present on the server.")
