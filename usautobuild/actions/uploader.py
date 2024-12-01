from ftplib import FTP, all_errors, error_perm
from logging import getLogger
from shutil import make_archive as zip_folder

from usautobuild.config import Config
from pathlib import Path 
import os
import zipfile
import json

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


    def check_good_file_version_folder_exists(self, version_number: str) -> bool:

        ftp = FTP()  # noqa: S321
        ftp.connect(self.config.cdn_host, 21, timeout=60)
        ftp.login(self.config.cdn_user, self.config.cdn_password)
     
        folder_path = f"/unitystation/GoodFiles/{version_number}"
        try:
            log.debug("Checking if folder %s exists...", folder_path)
            current_dir = ftp.pwd()  # Save the current directory
            ftp.cwd(folder_path)     # Try changing to the target directory
            ftp.cwd(current_dir)     # Change back to the original directory
            ftp.close()
            return True
        except error_perm as e:
            if "550" in str(e):  # 550 error indicates folder not found
                log.debug("Folder %s does not exist.", folder_path)
                return False
            ftp.close()
            raise e  # Re-raise other errors
        except all_errors as e:
            log.error("Error occurred while checking folder existence: %s", str(e))
            ftp.close()
            raise e
        ftp.close()


    def Zip_And_Upload_Good_files(self, version_number: str) -> None:
        """
        Zips and uploads individual target directories to the specified CDN path with filenames including the version.
        """
        if self.config.dry_run:
            log.info("Dry run enabled; skipping zip and upload of GoodFiles.")
            return
        
        ftp = FTP()  # noqa: S321
        try:
            log.debug("Connecting to CDN...")
            ftp.connect(self.config.cdn_host, 21, timeout=60)
            ftp.login(self.config.cdn_user, self.config.cdn_password)
            
            good_files_dir = Path(self.config.output_dir) / "good_files"
            for target in self.config.target_platforms:
                # Skip targets as needed
                if target == "linuxserver":
                    log.info("Skipping target: %s", target)
                    continue

                if target == "StandaloneLinux64":
                    continue

                if target == "StandaloneOSX":
                    continue

                
                # Prepare and zip the target directory
                target_path = good_files_dir / target
                zip_file_path = self.zip_directory(target_path, target, version_number)
                
                # Determine the remote file path based on the target
                target_suffix = {
                    "StandaloneWindows64": "Windows",
                    "StandaloneLinux64": "Linux",
                    "StandaloneOSX": "Mac",
                }.get(target, target)  # Default to target if unknown
                
                remote_file_name = f"{version_number}_{target_suffix}.zip"
                remote_path = f"/unitystation/GoodFiles/{version_number}/{remote_file_name}"
                
                # Upload the zipped file
                self.upload_file_to_ftp(ftp, zip_file_path, remote_path)
                log.info("Uploaded %s to %s", zip_file_path, remote_path)

                    # Now update the AllowGoodFiles.json file with the new version number
            allow_good_files_path = "/unitystation/GoodFiles/AllowGoodFiles.json"
            
            # Read the existing AllowGoodFiles.json
            try:
                log.debug("Reading existing AllowGoodFiles.json...")
                ftp.retrbinary(f"RETR {allow_good_files_path}", open("AllowGoodFiles.json", "wb").write)
                with open("AllowGoodFiles.json", "r") as file:
                    versions = json.load(file)
            except Exception as e:
                log.warning("Could not read AllowGoodFiles.json. Creating a new one.")
                versions = []

            # Append the new version number
            if version_number not in versions:
                versions.append(version_number)

            # Write the updated versions list to the file
            with open("AllowGoodFiles.json", "w") as file:
                json.dump(versions, file)

            # Upload the updated JSON file, overwriting the existing one
            with open("AllowGoodFiles.json", "rb") as file:
                log.debug("Uploading updated AllowGoodFiles.json...")
                ftp.storbinary(f"STOR {allow_good_files_path}", file)
                log.debug("AllowGoodFiles.json updated successfully.")
            
        except all_errors as e:
            log.error("An FTP error occurred: %s", str(e))
            raise e
        finally:
            ftp.close()
            log.debug("Disconnected from CDN.")

    def zip_directory(self, dir_path: Path, target: str, version_number: str) -> Path:
        # Determine the suffix for the target
        target_suffix = {
            "StandaloneWindows64": "Windows",
            "StandaloneLinux64": "Linux",
            "StandaloneOSX": "Mac",
        }.get(target, target)  # Default to target if unknown

        zip_file_name = f"{version_number}_{target_suffix}.zip"
        zip_file_path = dir_path.parent / zip_file_name
        log.debug("Zipping directory: %s to %s", dir_path, zip_file_path)
        
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(dir_path.parent)
                    zipf.write(file_path, arcname)
        log.debug("Zipping complete: %s", zip_file_path)
        return zip_file_path

    def upload_file_to_ftp(self, ftp: FTP, local_file: Path, remote_path: str) -> None:
        try:
            # Ensure the target directory exists on the FTP server
            remote_dir = "/".join(remote_path.split("/")[:-1])
            try:
                ftp.mkd(remote_dir)
            except error_perm:
                log.debug("Directory already exists on CDN: %s", remote_dir)

            with local_file.open("rb") as file:
                log.debug("Uploading file %s to %s...", local_file, remote_path)
                ftp.storbinary(f"STOR {remote_path}", file)
                log.debug("Upload complete for %s", remote_path)
        except all_errors as e:
            log.error("Error uploading file %s: %s", local_file, str(e))
            raise e
