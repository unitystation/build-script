from pathlib import Path


class BaseError(Exception):
    ...


class InvalidConfigFileError(BaseError):
    ...


class NoChangesError(BaseError):
    def __init__(self, branch: str) -> None:
        super().__init__(f"Found no changes on branch {branch}. Aborting the build!")


class InvalidProjectPathError(BaseError):
    def __init__(self) -> None:
        super().__init__("Path to unity project couldn't was invalid!")


class BuildFailedError(BaseError):
    def __init__(self, target: str) -> None:
        super().__init__(f"Build for {target} failed!")


class NugetRestoreFailedError(BaseError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Nuget restore failed in {path}! Is the path invalid or is NugetForUnity not installed?")


class MissingLicenseFileError(BaseError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"License file couldn't be found in set directory {path}")
