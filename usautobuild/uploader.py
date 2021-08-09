from ftplib import FTP, all_errors
from logging import getLogger
from pathlib import Path
from shutil import make_archive as zip_folder

from .config import Config

logger = getLogger("usautobuild")


class Uploader:
    def __init__(self, config: Config):
        self.cdn_host = config.cdn_host
        self.cdn_user = config.cdn_user
        self.cdn_password = config.cdn_password
        self.forkname = config.forkname
        self.target_platforms = config.target_platforms
        self.build_number = config.build_number
        self.output_dir = config.output_dir

    def upload_to_cdn(self):
        ftp = FTP()

        try:
            logger.debug("Trying to connect to CDN...")

            ftp.connect(self.cdn_host, 21, timeout=60)
            ftp.login(self.cdn_user, self.cdn_password)
            logger.debug(f"CDN says: {ftp.getwelcome()}")

            # ftp.rmd(f"/unitystation/{self.forkname}")
            # ftp.mkd(f"/unitystation/{self.forkname}")

            for target in self.target_platforms:
                self.attempt_ftp_upload(ftp, target)

        except all_errors as e:
            logger.error(str(e))
            raise e
        except Exception as e:
            logger.error(f"A non FTP problem occured while trying to upload to CDN")
            logger.error(f"{str(e)}")
            raise e

        ftp.close()

    def attempt_ftp_upload(self, ftp, target):
        ftp.mkd(f"/unitystation/{self.forkname}/{target}/")
        upload_path = f"/unitystation/{self.forkname}/{target}/{self.build_number}.zip"
        local_file = Path(self.output_dir, target, ".zip")
        try:
            with open(local_file, "rb") as zip_file:
                logger.debug(f"Uploading {target}...")
                ftp.storbinary(f"STOR {upload_path}", zip_file)
        except all_errors as e:
            if "timed out" in str(e):
                logger.debug("FTP connection timed out, retrying...")
                self.attempt_ftp_upload(ftp, target)
            else:
                logger.error(f"Error trying to upload {local_file}")
                logger.error(str(e))

    def zip_build_folder(self, target: str):
        build_folder = Path(self.output_dir, target)
        zip_folder(build_folder, 'zip', build_folder)

    def start_upload(self):
        logger.debug("Starting upload to cdn process...")

        for target in self.target_platforms:
            self.zip_build_folder(target)

        self.upload_to_cdn()
