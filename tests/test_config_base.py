import os

from pathlib import Path
from typing import Optional
from unittest import mock

import pytest

from usautobuild.config_base import ConfigBase, Var, VariableMissingError
from usautobuild.exceptions import InvalidConfigFileError


@pytest.fixture(autouse=True)
def clear_environ_by_default():
    with mock.patch.dict(os.environ, {}, clear=True):
        yield


def test_config_read_config_file():
    cfg = ConfigBase.read_config(Path(__file__).parent / "config_correct.json")

    assert cfg == {
        "a": "b",
        "c": [1, 2, 3],
        "d": 4,
        "e": 5.6,
    }


def test_config_read_config_file_malformed():
    with pytest.raises(InvalidConfigFileError, match="invalid"):
        ConfigBase.read_config(Path(__file__).parent / "config_malformed.json")


def test_config_read_config_file_not_map():
    with pytest.raises(InvalidConfigFileError, match="not a map"):
        ConfigBase.read_config(Path(__file__).parent / "config_not_map.json")


def test_config_read_config_file_nonexistent():
    cfg = ConfigBase.read_config(Path(__file__).parent / "config_nonexistent.json")

    assert cfg == {}


def test_config_sanitize_argparse_args():
    args = {
        "a": None,
        "b": 1,
        "c": False,
        "d": "e",
        "e": False,
        "f": None,
    }

    sanitized = ConfigBase.sanitize_argparse_args(args)

    assert None not in sanitized.values()
    assert False not in sanitized.values()


def test_config_annotated_values():
    class Config(ConfigBase):
        a: int
        b: float = 1.0
        c: Optional[str] = Var(None)

    cfg = Config(
        {
            "config_file": Path(),
            "a": "1",
            "c": "eggs",
        },
    )

    assert cfg.a == 1
    assert cfg.b == 1.0
    assert cfg.c == "eggs"


def test_config_non_annotated_values():
    class Config(ConfigBase):
        a = 1
        b = Var(2.0)

    cfg = Config(
        {
            "config_file": Path(),
            "a": "2",
        },
    )

    assert cfg.a == 2
    assert cfg.b == 2.0


def test_config_variable_missing():
    class Config(ConfigBase):
        a: int

    with pytest.raises(VariableMissingError):
        Config({"config_file": Path()})


@mock.patch.dict(os.environ, {"FOO": "1337"})
def test_config_attributes_properly_skipped():
    class Config(ConfigBase):
        foo: int

        _private_var = "spam"

        def method(self): ...

        async def async_method(self): ...

        @classmethod
        def class_method(cls): ...

        @staticmethod
        def static_method(): ...

        @property
        def property_method(self): ...

        @property_method.setter  # type: ignore[attr-defined]
        def setter(self): ...

        @property_method.getter  # type: ignore[attr-defined]
        def getter(self): ...

        @property_method.deleter  # type: ignore[attr-defined]
        def deleter(self): ...

    cfg = Config({"config_file": Path()})

    assert cfg.foo == 1337
    assert cfg._private_var == "spam"
