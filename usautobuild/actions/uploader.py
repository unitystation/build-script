import json
import os
import zipfile

from logging import getLogger
from pathlib import Path
from shutil import make_archive as zip_folder
from typing import TYPE_CHECKING, Optional

import boto3

from botocore.config import Config as BotoConfig

from usautobuild.config import Config

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

log = getLogger("usautobuild")

# Maps a build target to the suffix used in GoodFiles zip names.
GOOD_FILE_TARGET_SUFFIX = {
    "StandaloneWindows64": "Windows",
    "StandaloneLinux64": "Linux",
    "StandaloneOSX": "Mac",
}


class Uploader:
    def __init__(self, config: Config):
        self.config = config
        self._s3: "Optional[S3Client]" = None

    @property
    def s3(self) -> "S3Client":
        if self._s3 is None:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{self.config.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=self.config.r2_access_key_id,
                aws_secret_access_key=self.config.r2_secret_access_key,
                region_name="auto",
                config=BotoConfig(retries={"max_attempts": 10, "mode": "standard"}),
            )
        return self._s3

    def _upload_file(self, local_file: Path, key: str, content_type: str = "application/zip") -> None:
        log.debug("Uploading %s -> r2:%s/%s", local_file, self.config.r2_bucket, key)
        # upload_file handles multipart + retries automatically for large zips.
        self.s3.upload_file(
            str(local_file),
            self.config.r2_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    # -- regular build zips ------------------------------------------------
    def zip_build_folder(self, target: str) -> None:
        build_folder = self.config.output_dir / target
        zip_folder(str(build_folder), "zip", build_folder)

    def start_upload(self) -> None:
        if self.config.dry_run:
            log.info("Dry run, skipping upload")
            return

        log.debug("Starting upload to R2...")

        for target in self.config.target_platforms:
            self.zip_build_folder(target)

        self.upload_to_cdn()

    def upload_to_cdn(self) -> None:
        for target in self.config.target_platforms:
            local_file = (self.config.output_dir / target).with_suffix(".zip")
            key = f"{self.config.forkname}/{target}/{self.config.build_number}.zip"
            log.debug("Uploading %s...", target)
            self._upload_file(local_file, key)

    # -- good files --------------------------------------------------------
    def check_good_file_version_folder_exists(self, version_number: str) -> bool:
        prefix = f"GoodFiles/{version_number}/"
        log.debug("Checking if R2 prefix %s exists...", prefix)
        response = self.s3.list_objects_v2(Bucket=self.config.r2_bucket, Prefix=prefix, MaxKeys=1)
        return response.get("KeyCount", 0) > 0

    def zip_and_upload_good_files(self, version_number: str) -> None:
        """Zip each target's GoodFiles build, upload to GoodFiles/<version>/ in R2,
        then record the version in GoodFiles/AllowGoodFiles.json."""
        if self.config.dry_run:
            log.info("Dry run enabled; skipping zip and upload of GoodFiles.")
            return

        good_files_dir = Path(self.config.output_dir) / "good_files"
        for target in self.config.target_platforms:
            if target == "linuxserver":
                log.info("Skipping target: %s", target)
                continue

            target_path = good_files_dir / target
            zip_file_path = self.zip_directory(target_path, target, version_number)

            key = f"GoodFiles/{version_number}/{zip_file_path.name}"
            self._upload_file(zip_file_path, key)
            log.info("Uploaded %s to r2:%s/%s", zip_file_path, self.config.r2_bucket, key)

        self.update_allow_good_files(version_number)

    def update_allow_good_files(self, version_number: str) -> None:
        key = "GoodFiles/AllowGoodFiles.json"

        try:
            log.debug("Reading existing AllowGoodFiles.json...")
            response = self.s3.get_object(Bucket=self.config.r2_bucket, Key=key)
            versions = json.loads(response["Body"].read())
        except self.s3.exceptions.NoSuchKey:
            log.warning("AllowGoodFiles.json not found. Creating a new one.")
            versions = []
        except Exception as e:
            log.warning("Could not read AllowGoodFiles.json (%s). Creating a new one.", e)
            versions = []

        if version_number not in versions:
            versions.append(version_number)

        log.debug("Uploading updated AllowGoodFiles.json...")
        self.s3.put_object(
            Bucket=self.config.r2_bucket,
            Key=key,
            Body=json.dumps(versions).encode("utf-8"),
            ContentType="application/json",
        )
        log.debug("AllowGoodFiles.json updated successfully.")

    def zip_directory(self, dir_path: Path, target: str, version_number: str) -> Path:
        target_suffix = GOOD_FILE_TARGET_SUFFIX.get(target, target)

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
