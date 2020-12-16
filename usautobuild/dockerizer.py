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
    try:
        cmd = Popen("docker build -t unitystation/unitystation:develop Docker",
                    stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
        for line in cmd.stdout:
            logger.log(line)
        cmd.wait()

    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))


def push_image():
    logger.log("Pushing docker image")
    messager.send_success("Pushing docker image")
    try:
        cmd = Popen(f"docker login -p {os.environ['DOCKER_PASSWORD']} -u {os.environ['DOCKER_USERNAME']}",
                    stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
        cmd.wait()
    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))
        raise e
    try:
        cmd = Popen("docker push unitystation/unitystation:develop",
                    stdout=PIPE,
                    stderr=STDOUT,
                    universal_newlines=True,
                    shell=True)
    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))

    for line in cmd.stdout:
        logger.log(line)
    cmd.wait()


def start_dockering():
    logger.log("Starting docker process...")

    copy_server_build()
    make_image()
    push_image()

    finished = "Process finished, a new staging build has been deployed and should shortly be present on the server."
    logger.log(finished)
    messager.send_success(finished)
