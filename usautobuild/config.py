import json
import os
import typing

from collections.abc import Mapping
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, TypeVar, Union

from .exceptions import InvalidConfigFile

log = getLogger("usautobuild")


class _UnsetClass:
    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetClass()


class Variable:
    __slots__ = (
        "default",
        "type_",
        "arg",
        "config",
        "env",
    )

    def __init__(
        self,
        default: Any = _UNSET,
        *,
        type_: Optional[Any] = None,
        arg: Optional[str] = None,
        config: Optional[str] = None,
        env: Optional[str] = None,
    ):
        self.default = default
        self.type_ = type_
        self.arg = arg
        self.config = config
        self.env = env

    def resolve(self, name: str, type_: Optional[Any], args: Mapping[str, Any], cfg: dict[str, Any]) -> Any:
        if type_ is None:
            if self.default is _UNSET:
                raise ValueError(f"Need type annotation for {name} as there is no default value")

            type_ = type(self.default)

        value = self.default

        if (env := self.env) is None:
            env = name.upper()

        # special handling for env syntax, make sure we are not touching default
        if env in os.environ:
            value = self.convert_env(os.environ[env], type_)

        if (config := self.config) is None:
            config = name

        value = cfg.get(config, value)

        if (arg := self.arg) is None:
            arg = name

        value = args.get(arg, value)

        if value is _UNSET:
            raise ValueError(f"Missing required config value {name} / {env}")

        if typing.get_origin(type_) is Union:
            try:
                return self.convert_from_union(value, type_)
            except Exception as e:
                raise ValueError(f"Unable to convert {name} / {env} to any of union types: {e}")

        if type(value) is not type_:
            return type_(value)

        return value

    @staticmethod
    def convert_env(value: str, type_: Any) -> Any:
        if type_ is bool:
            if value.lower() in ("0", "no", "off", "disable", "false"):
                return False
            else:
                return True

        if type_ is list:
            return value.split(",")

        return value

    @staticmethod
    def convert_from_union(value: Any, type_: Union[Any]) -> Any:
        union_args = typing.get_args(type_)

        if type(value) not in union_args:
            # TODO: exception group when at 3.11
            errors = []
            for tp in union_args:
                try:
                    return tp(value)
                except Exception as e:
                    errors.append(e)

                raise ValueError(" ".join(map(str, errors)))

        return value

    def __repr__(self) -> str:
        fields = [type(self).__name__]
        for var in self.__slots__:
            if (value := getattr(self, var)) is not None:
                fields.append(f"{var}={value}")

        return f"<{' '.join(fields)}>"


T = TypeVar("T")


def Var(default: T = _UNSET, *args: Any, **kwargs: Any) -> T:  # type: ignore[assignment]
    return Variable(default, *args, **kwargs)  # type: ignore[return-value]


class Config:
    cdn_host: str
    cdn_user: str
    cdn_password: str
    docker_password: str
    docker_username: str
    changelog_api_url: str
    changelog_api_key: str

    git_url = Var("https://github.com/unitystation/unitystation.git")
    git_branch = Var("develop")

    unity_version = Var("2020.1.17f1")
    target_platforms = Var(["linuxserver", "StandaloneWindows64", "StandaloneOSX", "StandaloneLinux64"])
    cdn_download_url = Var("https://unitystationfile.b-cdn.net/{}/{}/{}.zip")
    forkname = Var("UnityStationDevelop")

    discord_webhook: Optional[str] = Var(None)

    dry_run = Var(False)
    abort_on_build_fail = Var(True)
    allow_no_changes = Var(True)

    build_number = Var(0)

    output_dir = Var(Path.cwd() / "builds")
    license_file = Var(Path.cwd() / "UnityLicense.ulf")
    project_path = Var(Path())

    def __init__(self, args: dict[str, Any]):
        # filter None and False (from store_true) values which break defaults handling
        args = {k: v for k, v in args.items() if v not in (None, False)}

        self.resolve_vars(args, self.read_config(args["config_file"]))

    @staticmethod
    def read_config(config_file: Path) -> dict[str, Any]:
        if not config_file.is_file():
            log.info("No config file found, we will proceed with all default")

            return {}

        try:
            with open(config_file) as f:
                config = json.load(f)
        except json.JSONDecodeError:
            raise InvalidConfigFile("JSON config file seems to be invalid!")

        if not isinstance(config, dict):
            raise InvalidConfigFile("Config is not a mapping")

        return config

    def resolve_vars(self, args: dict[str, Any], config: dict[str, Any]) -> None:
        # get vaiables with annotations:
        # foo: int
        # foo: int = Var(...)
        type_hints = typing.get_type_hints(type(self))

        # fill variables without annotations:
        # foo = Var(int, ...)
        for name, value in vars(type(self)).items():
            if not isinstance(value, Variable):
                continue

            if name not in type_hints:
                type_hints[name] = None

        for name, type_ in type_hints.items():
            # default for cases where Var is omitted:
            # foo: int
            var: Variable = getattr(self, name, Variable())

            try:
                setattr(self, name, var.resolve(name, type_, args, config))
            except Exception:
                log.error("resolving %s to %s of type %s", name, var, type_)

                raise

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {' '.join(f'{k}={v}' for k,v in self.__dict__.items())}>"
