from . import CONFIG, logger, messager
import shutil
import os
from subprocess import Popen, PIPE, STDOUT


def copy_server_build():
    if os.path.isdir("Docker/server"):
        shutil.rmtree("Docker/server")

    build_path = os.path.join(CONFIG["output_dir"], "linuxserver")
    shutil.copytree(build_path, "Docker/server")


def make_image():
    logger.log("Creating image")
    cmd = Popen("docker build -t unitystation/unitystation:develop Docker",
                stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    for line in cmd.stdout:
        logger.log(line)

    cmd.wait()
    rc = cmd.returncode
    logger.log(f"process says: {rc}")


def push_image():
    logger.log("Pushing docker image")
    try:
        cmd = Popen(f"docker login -p {os.environ['DOCKER_PASSWORD']} -u {os.environ['DOCKER_USERNAME']}",
                    stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        cmd.wait()
    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))
        raise e

    cmd = Popen("docker push unitystation/unitystation:develop", stdout=PIPE, stderr=STDOUT, universal_newlines=True)

    for line in cmd.stdout:
        logger.log(line)
    cmd.wait()


def start_dockering():
    logger.log("Starting docker process...")

    copy_server_build()
    make_image()
    push_image()

    logger.log("If everything went alright, go to portainer and recreate the container on staging")
    messager.send_success("Process finished. If everything went alright, we have deployed a new build!")
