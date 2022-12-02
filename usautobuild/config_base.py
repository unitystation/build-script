import inspect
import json
import os
import types
import typing

from collections.abc import Mapping
from logging import getLogger
from pathlib import Path
from typing import Any, Optional, TypeVar, Union

from .exceptions import InvalidConfigFile

__all__ = ("ConfigBase",)

log = getLogger("usautobuild")


class _UnsetClass:
    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetClass()


class Variable:
    """
    Represents a single variable in config.

    Arguments include default value (of final type), type override and custom names for CLI argument, config and env
    """

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
        """Look up value from chain of CLI -> config -> env -> default? and try converting it to appropriate type"""

        if self.type_ is not None:
            type_ = self.type_

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

        if typing.get_origin(type_) in (Union, types.UnionType):
            try:
                return self.convert_from_union(value, type_)
            except Exception as e:
                raise ValueError(f"Unable to convert {name} / {env} to any of union types: {e}")

        if type(value) is not type_:
            return type_(value)

        return value

    @staticmethod
    def convert_env(value: str, type_: Any) -> Any:
        """Dumb env parsing"""

        if type_ is bool:
            if value.lower() in ("0", "no", "off", "disable", "false"):
                return False
            else:
                return True

        if issubclass(type_, (int, float)):
            return type_(value)

        if typing.get_origin(type_) in (list, tuple) or issubclass(type_, (list, tuple)):
            if not value:
                return []

            return value.split(",")

        return value

    @staticmethod
    def convert_from_union(value: Any, type_: Union[Any]) -> Any:
        """Try converting value to any type in union"""

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
    """A helper function to assign Variable and forward default type"""

    return Variable(default, *args, **kwargs)  # type: ignore[return-value]


class ConfigBase:
    def __init__(self, args: dict[str, Any]):
        self.resolve_vars(
            self.sanitize_argparse_args(args),
            self.read_config(args["config_file"]),
        )

    @staticmethod
    def sanitize_argparse_args(args: dict[str, Any]) -> dict[str, Any]:
        """Filter None and False (from store_true) values which break defaults handling"""

        return {k: v for k, v in args.items() if v not in (None, False)}

    @staticmethod
    def read_config(config_file: Path) -> dict[str, Any]:
        """Attempt reading json config from filesystem"""

        if not config_file.is_file():
            log.warning("No config file found, we will proceed with all default")

            return {}

        try:
            with open(config_file) as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidConfigFile(f"Config contains invalid JSON: {e}")

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
        # foo = 1
        for name, value in inspect.getmembers(type(self)):
            if name.startswith("_"):
                continue

            if inspect.isfunction(value) or inspect.isdatadescriptor(value):
                continue

            if name not in type_hints:
                type_hints[name] = None

        for name, type_ in type_hints.items():
            # default for cases where Var is omitted:
            # foo: int
            var: Any = getattr(self, name, Variable())
            # variables with simple default:
            # foo = 1
            # foo: int = 1
            if not isinstance(var, Variable):
                var = Variable(var)

            try:
                setattr(self, name, var.resolve(name, type_, args, config))
            except Exception:
                log.error("resolving %s to %s of type %s", name, var, type_)

                raise

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {' '.join(f'{k}={v}' for k,v in self.__dict__.items())}>"
