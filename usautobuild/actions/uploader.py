from ftplib import FTP, all_errors, error_perm
from logging import getLogger
from shutil import make_archive as zip_folder

from usautobuild.action import Action, step

log = getLogger("usautobuild")


class Uploader(Action):
    MAX_UPLOAD_ATTEMPTS = 10

    @step(dry=True)
    def log_start(self) -> None:
        log.debug("Starting upload to cdn process...")

    @step()
    def zip_folders(self) -> None:
        for target in self.config.target_platforms:
            self.zip_build_folder(target)

    @step()
    def upload_to_cdn(self) -> None:
        ftp = FTP()

        try:
            log.debug("Trying to connect to CDN...")

            ftp.connect(self.config.cdn_host, 21, timeout=60)
            ftp.login(self.config.cdn_user, self.config.cdn_password)
            log.debug(f"CDN says: {ftp.getwelcome()}")

            # ftp.rmd(f"/unitystation/{self.forkname}")
            # ftp.mkd(f"/unitystation/{self.forkname}")

            for target in self.config.target_platforms:
                self.attempt_ftp_upload(ftp, target)

        except all_errors as e:
            log.error(str(e))
            raise e
        except Exception as e:
            log.error("A non FTP problem occured while trying to upload to CDN")
            log.error(str(e))
            raise e

        ftp.close()

    def attempt_ftp_upload(self, ftp: FTP, target: str, attempt: int = 0) -> None:
        try:
            ftp.mkd(f"/unitystation/{self.config.forkname}/{target}/")
        except error_perm:
            log.debug(f"Folder for {self.config.forkname} already exists!")
        except Exception as e:
            raise e

        upload_path = f"/unitystation/{self.config.forkname}/{target}/{self.config.build_number}.zip"
        local_file = (self.config.output_dir / target).with_suffix(".zip")
        try:
            with open(local_file, "rb") as zip_file:
                log.debug(f"Uploading {target}...")
                ftp.storbinary(f"STOR {upload_path}", zip_file)
        except all_errors as e:
            if "timed out" in str(e):
                if attempt >= self.MAX_UPLOAD_ATTEMPTS:
                    raise

                log.debug("FTP connection timed out, retrying...")
                self.attempt_ftp_upload(ftp, target, attempt=attempt + 1)
            else:
                log.error(f"Error trying to upload {local_file}")
                log.error(str(e))

    def zip_build_folder(self, target: str) -> None:
        build_folder = self.config.output_dir / target
        zip_folder(str(build_folder), "zip", build_folder)
