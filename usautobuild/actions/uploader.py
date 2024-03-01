from ftplib import FTP, all_errors, error_perm
from logging import getLogger
from shutil import make_archive as zip_folder

from usautobuild.config import Config

log = getLogger("usautobuild")


class Uploader:
    MAX_UPLOAD_ATTEMPTS = 10

    def __init__(self, config: Config):
        self.config = config

    def upload_to_cdn(self) -> None:
        # TODO: consider SFTP
        ftp = FTP()  # noqa: S321

        try:
            log.debug("Trying to connect to CDN...")

            ftp.connect(self.config.cdn_host, 21, timeout=60)
            ftp.login(self.config.cdn_user, self.config.cdn_password)
            log.debug("CDN says: %s", ftp.getwelcome())

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
            log.debug("Folder for %s already exists!", self.config.forkname)
        except Exception as e:
            raise e

        upload_path = f"/unitystation/{self.config.forkname}/{target}/{self.config.build_number}.zip"
        local_file = (self.config.output_dir / target).with_suffix(".zip")
        try:
            with local_file.open("rb") as zip_file:
                log.debug("Uploading %s...", target)
                ftp.storbinary(f"STOR {upload_path}", zip_file)
        except all_errors as e:
            if "timed out" in str(e):
                if attempt >= self.MAX_UPLOAD_ATTEMPTS:
                    raise

                log.debug("FTP connection timed out, retrying...")
                self.attempt_ftp_upload(ftp, target, attempt=attempt + 1)
            else:
                log.error("Error trying to upload %s", local_file)
                log.error(str(e))

    def zip_build_folder(self, target: str) -> None:
        build_folder = self.config.output_dir / target
        zip_folder(str(build_folder), "zip", build_folder)

    def start_upload(self) -> None:
        if self.config.dry_run:
            log.info("Dry run, skipping upload")
            return
        log.debug("Starting upload to cdn process...")

        for target in self.config.target_platforms:
            self.zip_build_folder(target)

        self.upload_to_cdn()
