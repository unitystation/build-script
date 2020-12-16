import os
import subprocess

from . import CONFIG, logger, messager

current_working_dir = os.getcwd()
unitystation_dir = os.path.join(current_working_dir, "unitystation")


def prepare_project_dir():
    if os.path.isdir(unitystation_dir):
        update_project()
    else:
        clone_project()


def update_project():
    try:
        os.chdir(unitystation_dir)
        logger.log("Updating the project to last state on github")
        shell = subprocess.Popen("git fetch --all && git checkout . && git clean -f && git rebase upstream/develop")
        shell.wait()
    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))
        raise e
    else:
        os.chdir(current_working_dir)


def clone_project():
    try:
        logger.log("Clonning the project from github")
        shell = subprocess.Popen(f"git clone {CONFIG['git_url']}")
        shell.wait()
    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))
        raise e

    if not os.path.isdir(os.path.join(".", "unitystation")):
        logger.log("Something went bad when trying to clone the project!")
        raise Exception("Something went bad when trying to clone the project!")

    CONFIG["project_path"] = os.path.join(".", "unitystation")


def start_gitting():
    prepare_project_dir()
