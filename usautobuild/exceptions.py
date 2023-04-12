from pathlib import Path


class BaseException(Exception):
    ...


class InvalidConfigFile(BaseException):
    ...


class NoChanges(BaseException):
    def __init__(self, branch: str) -> None:
        super().__init__(f"Found no changes on branch {branch}. Aborting the build!")


class InvalidProjectPath(BaseException):
    def __init__(self) -> None:
        super().__init__("Path to unity project couldn't was invalid!")


class BuildFailed(BaseException):
    def __init__(self, target: str) -> None:
        super().__init__(f"Build for {target} failed!")


class NugetRestoreFailed(BaseException):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Nuget restore failed in {path}! Is the path invalid or is NugetForUnity not installed?")

class MissingLicenseFile(BaseException):
    def __init__(self, path: Path) -> None:
        super().__init__(f"License file couldn't be found in set directory {path}")
