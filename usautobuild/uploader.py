from ftplib import FTP, all_errors
from logging import Logger
from pathlib import Path
from shutil import make_archive as zip_folder

from .config import Config

class Uploader:
    def __init__(self, config: Config, logger: Logger):
        self.logger = logger
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
            self.logger.debug("Trying to connect to CDN...")

            ftp.connect(self.cdn_host, 21, timeout=60)
            ftp.login(self.cdn_user, self.cdn_password)
            self.logger.debug(f"CDN says: {ftp.getwelcome()}")

            # ftp.rmd(f"/unitystation/{self.forkname}")
            # ftp.mkd(f"/unitystation/{self.forkname}")

            for target in self.target_platforms:
                self.attempt_ftp_upload(ftp, target)

        except all_errors as e:
            self.logger.error(str(e))
            raise e
        except Exception as e:
            self.logger.error(f"A non FTP problem occured while trying to upload to CDN")
            self.logger.error(f"{str(e)}")
            raise e

        ftp.close()

    def attempt_ftp_upload(self, ftp, target):
        ftp.mkd(f"/unitystation/{self.forkname}/{target}/")
        upload_path = f"/unitystation/{self.forkname}/{target}/{self.build_number}.zip"
        local_file = Path(self.output_dir, target, ".zip")
        try:
            with open(local_file, "rb") as zip_file:
                self.logger.debug(f"Uploading {target}...")
                ftp.storbinary(f"STOR {upload_path}", zip_file)
        except all_errors as e:
            if "timed out" in str(e):
                self.logger.debug("FTP connection timed out, retrying...")
                self.attempt_ftp_upload(ftp, target)
            else:
                self.logger.error(f"Error trying to upload {local_file}")
                self.logger.error(str(e))

    def zip_build_folder(self, target: str):
        build_folder = Path(self.output_dir, target)
        zip_folder(build_folder, 'zip', build_folder)

    def start_upload(self):
        self.logger.debug("Starting upload to cdn process...")

        for target in self.target_platforms:
            self.zip_build_folder(target)

        self.upload_to_cdn()