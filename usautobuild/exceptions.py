class BaseException(Exception):
    pass


class MissingRequiredEnv(BaseException):
    def __init__(self, name_env):
        super(MissingRequiredEnv, self).__init__(
            f"Missing a required environmental variable: {name_env}"
        )

class MissingRequiredConfig(BaseException):
    def __init__(self, name_config):
        super(MissingRequiredConfig, self).__init__(
            f"Missing a required configuration from the config file: {name_config}"
        )

class MissingConfigFile(BaseException):
    def __init__(self, path):
        super(MissingConfigFile, self).__init__(
            f"Couldn't find config file in the set directory: {path}"
        )

class InvalidConfigFile(BaseException):
    def __init__(self):
        super(InvalidConfigFile, self).__init__(
            "The config file seems to be an invalid JSON file."
        )

class NoChanges(BaseException):
    def __init__(self, branch: str):
        super(NoChanges, self).__init__(
            f"Found no changes on branch {branch}. Aborting the build!"
        )

class InvalidProjectPath(BaseException):
    def __init__(self):
        super(InvalidProjectPath, self).__init__(
            "Path to unity project couldn't was invalid!"
        )

class BuildFailed(BaseException):
    def __init__(self, target):
        super(BuildFailed, self).__init__(
            f"Build for {target} failed!"
        )

class MissingLicenseFile(BaseException):
    def __init__(self, path):
        super(MissingLicenseFile, self).__init__(
            f"License file couldn't be found in set directory {path}"
        )