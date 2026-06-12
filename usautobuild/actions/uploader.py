import datetime
import json
import os
import zipfile

from concurrent.futures import ThreadPoolExecutor
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

# Only cache zips for long time
ZIP_CACHE_CONTROL = "public, max-age=31536000, immutable"


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

    @property
    def primary_bucket(self) -> str:
        return self.config.r2_buckets[0]

    def _upload_file(self, local_file: Path, key: str, content_type: str = "application/zip") -> None:
        extra_args = {"ContentType": content_type}
        if key.endswith(".zip"):
            extra_args["CacheControl"] = ZIP_CACHE_CONTROL

        log.debug("Uploading %s -> r2:%s/%s", local_file, self.primary_bucket, key)
        # upload_file handles multipart + retries automatically for large zips.
        self.s3.upload_file(str(local_file), self.primary_bucket, key, ExtraArgs=extra_args)
        self._replicate(key)

    def _replicate(self, key: str) -> None:
        """Copy a file from the primary bucket to the regional buckets.
        The copy happens inside R2 itself, so nothing gets re-uploaded.
        If a regional copy fails the build carries on and the CDN worker
        just serves missing files from the primary bucket instead."""
        replicas = self.config.r2_buckets[1:]
        if not replicas:
            return

        source = {"Bucket": self.primary_bucket, "Key": key}
        with ThreadPoolExecutor(max_workers=len(replicas)) as pool:
            futures = {pool.submit(self.s3.copy, source, bucket, key): bucket for bucket in replicas}

        for future, bucket in futures.items():
            error = future.exception()
            if error is not None:
                log.error("Failed to replicate %s to regional bucket %s: %s", key, bucket, error)

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
        self.prune_old_builds()

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
        response = self.s3.list_objects_v2(Bucket=self.primary_bucket, Prefix=prefix, MaxKeys=1)
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
            log.info("Uploaded %s to r2 buckets %s under %s", zip_file_path, self.config.r2_buckets, key)

        self.update_allow_good_files(version_number)

    def update_allow_good_files(self, version_number: str) -> None:
        key = "GoodFiles/AllowGoodFiles.json"

        try:
            log.debug("Reading existing AllowGoodFiles.json...")
            response = self.s3.get_object(Bucket=self.primary_bucket, Key=key)
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
            Bucket=self.primary_bucket,
            Key=key,
            Body=json.dumps(versions).encode("utf-8"),
            ContentType="application/json",
        )
        self._replicate(key)
        log.debug("AllowGoodFiles.json updated successfully.")

    # -- pruning -------------------------------------------------------------
    def prune_old_builds(self) -> None:
        """Delete old build zips from every bucket, keeping the newest
        prune_keep_builds count per platform plus anything younger than
        prune_min_age_days. Touches only the {forkname}/ build archive, never
        GoodFiles or anything else."""
        keep_n = self.config.prune_keep_builds
        if keep_n <= 0:
            log.info("Build pruning disabled (prune_keep_builds=0)")
            return

        # Floor age is determined by YYMMDDHH timestamps
        floor_date = datetime.datetime.now() - datetime.timedelta(days=self.config.prune_min_age_days)
        age_floor = int(floor_date.strftime("%y%m%d%H"))

        for target in self.config.target_platforms:
            prefix = f"{self.config.forkname}/{target}/"
            builds = self._list_build_numbers(prefix)
            builds.sort(reverse=True)

            doomed = [number for number in builds[keep_n:] if number < age_floor]
            if not doomed:
                log.info("Prune %s: nothing to delete (%d builds)", target, len(builds))
                continue

            log.info(
                "Prune %s: deleting %d of %d builds (keeping newest %d + anything since %d): %s",
                target, len(doomed), len(builds), keep_n, age_floor, doomed,
            )
            if self.config.dry_run:
                continue

            keys = [f"{prefix}{number}.zip" for number in doomed]
            for bucket in self.config.r2_buckets:
                try:
                    # delete_objects takes at most 1000 keys per call.
                    for start in range(0, len(keys), 1000):
                        batch = keys[start : start + 1000]
                        self.s3.delete_objects(
                            Bucket=bucket,
                            Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
                        )
                except Exception as e:
                    # A failed prune must never fail the build; stale zips only cost storage.
                    log.error("Prune failed in bucket %s: %s", bucket, e)

    def _list_build_numbers(self, prefix: str) -> "list[int]":
        """List the build numbers for one platform from the primary bucket.
        Build filenames are 8-digit timestamps like 26060701. Anything not
        named that way is ignored, so the pruner can not touch it."""
        numbers = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.primary_bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                stem = obj["Key"].rsplit("/", 1)[-1].removesuffix(".zip")
                if stem.isdigit() and len(stem) == 8:
                    numbers.append(int(stem))
        return numbers

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
