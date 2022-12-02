import os

from typing import Optional, Union
from unittest import mock

import pytest

from usautobuild.config_base import Var, Variable


@pytest.fixture(autouse=True)
def clear_environ_by_default():
    with mock.patch.dict(os.environ, {}, clear=True):
        yield


def test_var_returns_variable():
    default = 1
    type_ = str
    arg = "arg"
    config = "config"
    env = "env"

    # type ignore because of typevar magic
    var: Variable = Var(default, type_=type_, arg=arg, config=config, env=env)  # type: ignore[assignment]

    assert isinstance(var, Variable)
    assert var.default == default
    assert var.type_ == type_
    assert var.arg == arg
    assert var.config == config
    assert var.env == env


def test_variable_env_parser_type_unknown():
    value = "test string, hello"

    result = Variable.convert_env(value, object)

    assert result == value


def test_variable_env_parser_type_bool():
    assert Variable.convert_env("1", bool) is True
    assert Variable.convert_env("", bool) is True
    assert Variable.convert_env("YES", bool) is True

    assert Variable.convert_env("0", bool) is False
    assert Variable.convert_env("oFf", bool) is False
    assert Variable.convert_env("NO", bool) is False
    assert Variable.convert_env("FAlse", bool) is False
    assert Variable.convert_env("disable", bool) is False


def test_variable_env_parser_type_number():
    assert Variable.convert_env("1", int) == 1
    assert Variable.convert_env("-0.2", float) == float("-0.2")


def test_variable_env_parser_type_list_str():
    assert Variable.convert_env("1,2", list[str]) == ["1", "2"]
    assert Variable.convert_env("3", list) == ["3"]
    assert Variable.convert_env("", list) == []
    assert Variable.convert_env(",,,,", list[str]) == ["", "", "", "", ""]


@pytest.mark.xfail(reason="strict tuples are not yet implemented")
def test_variable_env_parser_type_tuple_str():
    # tuple bug: https://github.com/python/mypy/issues/11098
    assert Variable.convert_env("1,2", tuple[str, str]) == ["1", "2"]  # type: ignore[misc]
    assert Variable.convert_env("", tuple) == []
    assert Variable.convert_env(",,,,", tuple[str, str, str, str]) == ["", "", "", "", ""]  # type: ignore[misc]

    with pytest.raises(ValueError):
        assert Variable.convert_env(",,,,", tuple[str]) == ["", "", "", "", ""]


@pytest.mark.xfail(reason="non str iterables are not yet implemented")
def test_variable_env_parser_type_list_non_str():
    assert Variable.convert_env("1,2", list[int]) == [1, 2]
    assert Variable.convert_env("3", tuple[int]) == [3]


def test_variable_resolve_expects_default_or_type():
    var = Variable()

    with pytest.raises(ValueError, match="Need type annotation"):
        var.resolve("name", None, {}, {})


def test_variable_resolve_prefers_its_own_type():
    var = Variable("1", type_=int)

    assert var.resolve("var", float, {}, {"var": "2"}) == 2


def test_variable_resolve_gets_type_from_default():
    var = Variable(1)

    assert var.resolve("name", None, {"name": "2"}, {}) == 2


def test_variable_resolve_variable_missing():
    var = Variable()

    with pytest.raises(ValueError, match="Missing required"):
        var.resolve("nonexistent", int, {}, {})


def test_variable_resolve_do_nothing_if_already_converted():
    sentinel = object()
    var = Variable(sentinel)

    # object errors when called
    assert var.resolve("foo", object, {}, {}) == sentinel


@mock.patch.dict(os.environ, {"FOO": "42"})
def test_variable_resolve_gets_resolves_env():
    var = Variable()

    assert var.resolve("foo", int, {}, {}) == 42


def test_variable_resolve_gets_resolves_config():
    var = Variable()

    assert var.resolve("foo", int, {}, {"foo": "42"}) == 42


def test_variable_resolve_gets_resolves_args():
    var = Variable()

    assert var.resolve("foo", int, {"foo": "42"}, {}) == 42


def test_variable_resolve_env_not_trying_to_parse_default():
    var = Variable("1,2")

    assert var.resolve("foo", list[str], {}, {}) == ["1", ",", "2"]


@mock.patch.dict(os.environ, {"FOO": "43"})
def test_variable_resolve_prefers_env_over_default():
    var = Variable(42)

    assert var.resolve("FOO", None, {}, {}) == 43


@mock.patch.dict(os.environ, {"FOO": "42"})
def test_variable_resolve_prefers_config_over_env():
    var = Variable()

    assert var.resolve("FOO", int, {}, {"FOO": "43"}) == 43


def test_variable_resolve_prefers_cli_over_config():
    var = Variable()

    assert var.resolve("foo", int, {"foo": "43"}, {"foo": "42"}) == 43


@mock.patch.dict(os.environ, {"FOO": "40"})
def test_variable_resolve_prefers_cli_over_everything():
    var = Variable(41)

    assert var.resolve("foo", int, {"foo": "42"}, {"FOO": "43"}) == 42


def test_variable_resolve_optional():
    type_ = Optional[int]

    var1 = Variable(type_=type_)
    var2 = Variable(type_=type_)

    assert var1.resolve("foo", None, {}, {"foo": None}) is None
    assert var2.resolve("foo", None, {}, {"foo": "1"}) == 1


def test_variable_resolve_union():
    # these are actually different types
    var1 = Variable(type_=int | float)
    var2 = Variable(type_=Union[int, float])

    assert var1.resolve("bar", None, {}, {"bar": "0.0"}) == float("0.0")
    assert var2.resolve("bar", None, {}, {"bar": "0.0"}) == float("0.0")


def test_variable_resolve_no_valid_options():
    var = Variable()

    with pytest.raises(ValueError):
        var.resolve("foo", int | float, {"foo": "test"}, {})


@mock.patch.dict(os.environ, {"foo_lowercase": "42"})
def test_variable_resolve_env_overwrite():
    var = Variable(env="foo_lowercase")

    assert var.resolve("foo_lowercase", int, {}, {}) == 42


def test_variable_resolve_config_overwrite():
    var = Variable(config="bar")

    assert var.resolve("something else", int, {}, {"bar": "42"}) == 42


def test_variable_resolve_cli_overwrite():
    var = Variable(arg="baz")

    assert var.resolve("something else", int, {"baz": "42"}, {}) == 42
