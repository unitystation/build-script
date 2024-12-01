import json
import re
import shutil
import time
import os

from logging import getLogger
from pathlib import Path

import humanize

from usautobuild.config import Config
from usautobuild.exceptions import (
    BuildFailedError,
    InvalidProjectPathError,
    MissingLicenseFileError
)
from usautobuild.utils import git_version, run_process_shell

log = getLogger("usautobuild")


class good_files:
    def __init__(self, config):
        self.config = config
        self.files_to_keep_in_managed = self.get_files_to_keep_in_managed()

    def get_files_to_keep_in_managed(self):
        path = Path.cwd() / "local_repo/Tools/CodeScanning/CodeScan/CodeScan/bin/Debug/net7.0/FilesToMoveToManaged.json"
        with open(path, 'r') as file:
            return json.load(file)

    def make_good_files_build(self, VersionTag) -> None:
        good_files_dir = Path(self.config.output_dir) / "good_files"
        good_files_dir.mkdir(parents=True, exist_ok=True)

        # Check if bundledDLL/version.txt exists and verify the version
        self.check_version()
        
        for target in self.config.target_platforms:
            if target == "linuxserver":
                print("Skipping %s", target)
                continue

            if target == "StandaloneLinux64":
                print("Skipping %s", target)
                continue

            if target == "StandaloneOSX":
                print("Skipping %s", target)
                continue

            
            target_path = Path(self.config.output_dir) / target
            if target_path.exists() and target_path.is_dir():
                destination = good_files_dir / target
                shutil.copytree(target_path, destination, dirs_exist_ok=True)
                self.prepare_target(target, destination)
            else:
                print("Target path %s does not exist or is not a directory", target_path)

    def check_version(self):
        version_file = Path.cwd() / "bundledDLL" / "version.txt"
        if version_file.exists():
            with open(version_file, 'r') as file:
                version_info = json.load(file)
                version = version_info.get("Version")
                if version != self.config.unity_version:
                    raise BuildFailedError(f"Version mismatch: Expected {self.config.unity_version}, but found {version}")
        else:
            raise BuildFailedError("bundledDLL/version.txt not found")

    def prepare_target(self, target, path):
        if target == "StandaloneWindows64":
            self.prepare_windows(path)
        elif target == "StandaloneLinux64":
            self.prepare_linux(path)
        elif target == "StandaloneOSX":
            self.prepare_mac(path)
        else:
            log.warning("Unknown target platform: %s", target)

    def prepare_windows(self, path):
        managed_dir = os.path.join(path, "Unitystation_Data", "Managed")
        self.clean_managed(managed_dir)
        self.copy_bundled_dlls("StandaloneWindows64", managed_dir)
        shutil.rmtree(os.path.join(path, "Unitystation_Data", "Resources"), ignore_errors=True)
        shutil.rmtree(os.path.join(path, "Unitystation_Data", "StreamingAssets"), ignore_errors=True)
        self.clean_files_in_directory(os.path.join(path, "Unitystation_Data"))

    def prepare_linux(self, path):
        managed_dir = os.path.join(path, "Unitystation_Data", "Managed")
        self.clean_managed(managed_dir)
        self.copy_bundled_dlls("StandaloneLinux64", managed_dir)
        shutil.rmtree(os.path.join(path, "Unitystation_Data", "Resources"), ignore_errors=True)
        shutil.rmtree(os.path.join(path, "Unitystation_Data", "StreamingAssets"), ignore_errors=True)
        self.clean_files_in_directory(os.path.join(path, "Unitystation_Data"))

    def prepare_mac(self, path):
        managed_dir = os.path.join(path, "Unitystation.app", "Contents", "Resources", "Data", "Managed")
        self.clean_managed(managed_dir)
        self.copy_bundled_dlls("StandaloneOSX", managed_dir)
        shutil.rmtree(os.path.join(path, "Unitystation.app", "Contents", "Resources", "Data", "StreamingAssets"), ignore_errors=True)
        self.clean_files_in_directory(os.path.join(path, "Unitystation.app", "Contents", "Resources", "Data"))

    def copy_bundled_dlls(self, target, managed_dir):
        bundled_dll_dir = Path.cwd() / "bundledDLL" / target  # Use Path.cwd() and target to form the source path
        if bundled_dll_dir.exists():
            for dll in os.listdir(bundled_dll_dir):
                dll_path = bundled_dll_dir / dll
                if dll_path.is_file():
                    shutil.copy2(dll_path, os.path.join( managed_dir, dll))  # Copy and overwrite files
        else:
            log.warning("Bundled DLL directory does not exist: %s", bundled_dll_dir)

    def clean_managed(self, managed_dir):
        for file in os.listdir(managed_dir):
            file_path = os.path.join(managed_dir, file)
            if os.path.isfile(file_path):
                file_name, _ = os.path.splitext(file)
                if file_name not in self.files_to_keep_in_managed:
                    os.remove(file_path)

    def clean_files_in_directory(self, dir_path):
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
