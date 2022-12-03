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

__all__ = (
    "ConfigBase",
    "BaseConversionException",
    "TypeAnnotationNeeded",
    "VariableMissing",
    "VariableInvalid",
)

log = getLogger("usautobuild")


class _UnsetClass:
    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetClass()


class BaseConversionException(Exception):
    __slots__ = (
        "var",
        "message",
        "name",
    )

    def __init__(self, message: str):
        self.message = message

        self.var: Optional[Variable] = None
        self.name: Optional[str] = None

    def __str__(self) -> str:
        if (name := self.name) is not None and (var := self.var) is not None:
            prefix = f"[{var.env_name(name)} / {name}] "
        else:
            prefix = ""

        return f"{prefix}{self.message}"


class TypeAnnotationNeeded(BaseConversionException):
    def __init__(self, message: str = "Need type annotation as there is no default value"):
        super().__init__(message)


class VariableMissing(BaseConversionException):
    def __init__(self, message: str = "Missing required value"):
        super().__init__(message)


class VariableInvalid(BaseConversionException):
    def __init__(self, message: str = "Bad value"):
        super().__init__(message)


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
        "set_env",
    )

    def __init__(
        self,
        default: Any = _UNSET,
        *,
        type_: Any = _UNSET,
        arg: Optional[str] = None,
        config: Optional[str] = None,
        env: Optional[str] = None,
        set_env: bool = True,
    ):
        self.default = default
        self.type_ = type_
        self.arg = arg
        self.config = config
        self.env = env
        self.set_env = set_env

    def resolve(self, name: str, args: Mapping[str, Any], cfg: dict[str, Any], type_: Any = _UNSET) -> Any:
        """Look up value from chain of CLI -> config -> env -> default? and try converting it to appropriate type"""

        try:
            return self._resolve(name, args, cfg, type_)
        except BaseConversionException as e:
            e.name = name
            e.var = self

            raise

    def _resolve(self, name: str, args: Mapping[str, Any], cfg: dict[str, Any], type_: Any) -> Any:
        if self.type_ is not _UNSET:
            type_ = self.type_

        if type_ is _UNSET:
            type_ = self.guess_type_from_default(self.default)

        value, from_env = self.fetch_value(name, args, cfg)

        if from_env:
            return self.convert_env(value, type_)

        converted_value = self.convert_non_env(value, type_)

        # overwrite environ only after successful conversion
        # if we got variable from env we do not need to overwrite it
        if self.set_env:
            os.environ[self.env_name(name)] = str(value)

        return converted_value

    @staticmethod
    def guess_type_from_default(default: Any) -> Any:
        """Best effort type guess from default"""

        if default is _UNSET:
            raise TypeAnnotationNeeded

        if inspect.isclass(default):
            return default

        if callable(default):
            signature = inspect.signature(default, eval_str=True)
            if (return_annotation := signature.return_annotation) == inspect.Signature.empty:
                raise TypeAnnotationNeeded("Need type annotation as default callable is untyped")

            return return_annotation

        return type(default)

    def fetch_value(self, name: str, args: Mapping[str, Any], cfg: dict[str, Any]) -> tuple[Any, bool]:
        """
        Get value from different sources with prioritios of CLI -> config -> env -> default.

        Second value indicates if value was fetched from env because env variables need special treatment.
        """

        if (arg := self.arg) is None:
            arg = name

        if arg in args:
            return args[arg], False

        if (config := self.config) is None:
            config = name

        if config in cfg:
            return cfg[config], False

        if (env := self.env_name(name)) in os.environ:
            return os.environ[env], True

        if self.default is _UNSET:
            raise VariableMissing

        return self.default, False

    def env_name(self, name: str) -> str:
        """Convert variable name to approprieate env name"""

        if (env := self.env) is not None:
            return env

        return name.upper().replace("-", "_")

    @staticmethod
    def convert_env(value: str, type_: Any) -> Any:
        """Dumb env parsing"""

        if type_ is bool:
            if value.lower() in ("0", "no", "off", "disable", "false"):
                return False
            else:
                return True

        if inspect.isclass(type_) and (typing.get_origin(type_) in (list, tuple) or issubclass(type_, (list, tuple))):
            if not value:
                return []

            return value.split(",")

        try:
            return type_(value)
        except Exception as e:
            raise VariableInvalid(str(e))

    @classmethod
    def convert_non_env(cls, value: Any, type_: Any) -> Any:
        if type(value) is type_:
            return value

        if typing.get_origin(type_) in (Union, types.UnionType):
            try:
                return cls.convert_from_union(value, type_)
            except Exception as e:
                raise VariableInvalid(f"Unable to convert to any of union types: [{e}]")

        try:
            return type_(value)
        except Exception as e:
            raise VariableInvalid(str(e))

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

            raise VariableInvalid("; ".join(f"{tp}: {e}" for tp, e in zip(union_args, errors)))

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
        variables = typing.get_type_hints(type(self))

        # fill variables without annotations:
        # foo = Var(int, ...)
        # foo = 1
        for name, value in inspect.getmembers(type(self)):
            if name.startswith("_"):
                continue

            if inspect.isfunction(value) or inspect.isdatadescriptor(value) or inspect.ismethod(value):
                continue

            if name not in variables:
                variables[name] = _UNSET

        for name, type_ in variables.items():
            # default for cases where Var is omitted:
            # foo: int
            var: Any = getattr(self, name, Variable())
            # variables with simple default:
            # foo = 1
            # foo: int = 1
            if not isinstance(var, Variable):
                var = Variable(var)

            try:
                setattr(self, name, var.resolve(name, args, config, type_=type_))
            except Exception as e:
                log.error("resolving %s to %s of type %s", name, var, type_)

                raise e from None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {' '.join(f'{k}={v}' for k,v in self.__dict__.items())}>"
