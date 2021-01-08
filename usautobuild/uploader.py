from . import CONFIG, logger, messager
from shutil import make_archive as zip_folder
import os
from ftplib import FTP, all_errors


def upload_to_cdn():
    ftp = FTP()

    try:
        logger.log("Trying to connect to CDN")
        ftp.connect(CONFIG["CDN_HOST"], 21, timeout=60)
        ftp.login(CONFIG["CDN_USER"], CONFIG["CDN_PASSWORD"])
        logger.log(f"CDN says: {ftp.getwelcome()}")
        ftp.rmd(f"/unitystation/{CONFIG['forkName']}")
        ftp.mkd(f"/unitystation/{CONFIG['forkName']}")

        for target in CONFIG["target_platform"]:
            attempt_ftp_upload(ftp, target)
    except all_errors as e:
        logger.log(f"Found FTP error: {str(e)}")
        raise e
    except Exception as e:
        logger.log(f"A non FTP problem occured while trying to upload to CDN")
        logger.log(f"{str(e)}")
        raise e

    ftp.close()


def attempt_ftp_upload(ftp, target):
    ftp.mkd(f"/unitystation/{CONFIG['forkName']}/{target}/")
    upload_path = f"/unitystation/{CONFIG['forkName']}/{target}/{str(CONFIG['build_number'])}.zip"
    local_file = os.path.join(CONFIG["output_dir"], target + ".zip")
    try:
        with open(local_file, "rb") as zip_file:
            logger.log(f"Uploading {target}...")
            # messager.send_success(f"Uploading {target}")
            ftp.storbinary(f"STOR {upload_path}", zip_file)
    except all_errors as e:
        if "timed out" in str(e):
            logger.log("FTP connection timed out, retrying...")
            attempt_ftp_upload(ftp, target)
        else:
            logger.log(f"Error trying to upload {local_file}")
            messager.send_fail(f"Error trying to upload {local_file}")
            logger.log(str(e))


def zip_build_folder(target: str):
    build_folder = f"{os.path.join(CONFIG['output_dir'], target)}"
    output = f"{os.path.join(CONFIG['output_dir'], target)}"

    zip_folder(output, 'zip', build_folder)


def start_upload():
    logger.log("Starting upload to cdn process...")

    for target in CONFIG["target_platform"]:
        zip_build_folder(target)

    upload_to_cdn()
