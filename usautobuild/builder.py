import json
import shutil
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

from . import CONFIG, logger, messager
import os

exec_name = {
    "linuxserver": "Unitystation",
    "StandaloneLinux64": "Unitystation",
    "StandaloneWindows64": "Unitystation.exe",
    "StandaloneOSX": "Unitystation.app"
}

platform_image = {
    "linuxserver": "",
    "StandaloneLinux64": "",
    "StandaloneWindows64": "-windows",
    "StandaloneOSX": "-mac"
}


def get_real_target(target: str):
    if target.lower() == "linuxserver":
        return "StandaloneLinux64"

    return target


def get_devBuild_flag(target: str):
    if target.lower() == "linuxserver":
        return "-devBuild"

    return ""


def make_command(target: str):
    return \
        f"docker run --rm " \
        f"-v {CONFIG['project_path']}:/root/UnityProject " \
        f"-v {os.path.join(os.getcwd(), 'license')}:/root/.local/share/unity3d/Unity " \
        f"-v {os.path.join(os.getcwd(), 'builds')}:/root/builds " \
        f"-v {os.path.join(os.getcwd(), 'logs')}:/root/logs " \
        f"gableroux/unity3d:{CONFIG['unity_version']}{platform_image[target]} " \
        f"/opt/Unity/Editor/Unity " \
        f"-batchmode -nographics " \
        f"-projectPath /root/UnityProject " \
        f"-buildTarget {get_real_target(target)} " \
        f"-executeMethod BuildScript.BuildProject " \
        f"-customBuildPath {os.path.join('/root', 'builds', target, exec_name[target])} " \
        f"{get_devBuild_flag(target)} " \
        f"-logfile /root/logs/{target}.txt " \
        f"-quit"


def build(command: str, target: str):
    try:
        logger.log(command)
        cmd = Popen(command, stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
        for line in cmd.stdout:
            if line.strip():
                logger.log(line)
            if "Build succeeded!" in line:
                CONFIG[f"{target}_build_status"] = "success"
        cmd.wait()
        exit_code = cmd.returncode

    except Exception as e:
        logger.log(str(e))
        messager.send_fail(str(e))
        raise e

    CONFIG[f"{target}_build_status"] = "success" if exit_code == 0 else "fail"

    if CONFIG["abort_on_build_fail"] and CONFIG[f"{target}_build_status"] == "fail":
        logger.log(f"build for {target} failed and config is set to abort process on fail, aborting")
        messager.send_fail(f"build for {target} failed and config is set to abort process on fail, aborting")
        raise Exception("A build failed and config is set to abort on fail")


def get_build_number():
    CONFIG["build_number"] = datetime.now().strftime("%y%m%d%H")


def create_builds_folder():
    for target in CONFIG["target_platform"]:
        try:
            os.makedirs(
                os.path.join(os.getcwd(), CONFIG["output_dir"], target), exist_ok=True)
        except Exception as e:
            logger.log(str(e))


def set_jsons_data():
    build_info = os.path.join(CONFIG["project_path"], "Assets", "StreamingAssets", "buildinfo.json")
    config_json = os.path.join(CONFIG["project_path"], "Assets", "StreamingAssets", "config", "config.json")

    with open(build_info) as read:
        p_build_info = json.loads(read.read())

    with open(config_json) as read:
        p_config_json = json.loads(read.read())

    with open(build_info, "w") as json_data:
        p_build_info["BuildNumber"] = CONFIG["build_number"]
        p_build_info["ForkName"] = CONFIG["forkName"]
        json.dump(p_build_info, json_data, indent=4)

    with open(config_json, "w") as json_data:
        url = CONFIG["CDN_DOWNLOAD_URL"]
        p_config_json["WinDownload"] = url.format(CONFIG["forkName"], "StandaloneWindows64", CONFIG["build_number"])
        p_config_json["OSXDownload"] = url.format(CONFIG["forkName"], "StandaloneOSX", CONFIG["build_number"])
        p_config_json["LinuxDownload"] = url.format(CONFIG["forkName"], "StandaloneLinux64", CONFIG["build_number"])
        json.dump(p_config_json, json_data, indent=4)


def clean_builds_folder():
    for target in CONFIG['target_platform']:
        folder = os.path.join(os.getcwd(), CONFIG["output_dir"], target)

        if os.path.isdir(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                logger.log((str(e)))


def start_building():
    logger.log("Starting build process...")
    messager.send_success("Starting a new build!")
    get_build_number()
    clean_builds_folder()
    create_builds_folder()
    set_jsons_data()

    for target in CONFIG["target_platform"]:
        logger.log(f"\n****************\nStarting build of {target}...\n****************\n")
        # messager.send_success(f"Starting build of {target}")
        build(make_command(target), target)

    logger.log("\n\n*************************************************\n\n")
    for target in CONFIG["target_platform"]:
        logger.log(f"Build for {target} was a {CONFIG[target + '_build_status']}")
    logger.log("\n\n*************************************************\n\n")
