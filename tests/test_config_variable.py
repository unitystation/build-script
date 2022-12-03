import os

from typing import Optional, Union
from unittest import mock

import pytest

from usautobuild.config_base import TypeAnnotationNeeded, Var, Variable, VariableInvalid, VariableMissing


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


def test_variable_env_name():
    var = Variable()

    assert var.env_name("spam") == "SPAM"
    assert var.env_name("foo-bar") == "FOO_BAR"


def test_variable_env_name_uses_overwrite():
    var = Variable(env="lowercase-foo")

    assert var.env_name("foo") == "lowercase-foo"


def test_variable_convert_env_unknown():
    value = "test string, hello"

    result = Variable.convert_env(value, object)

    assert result == value


def test_variable_convert_env_bool():
    assert Variable.convert_env("1", bool) is True
    assert Variable.convert_env("", bool) is True
    assert Variable.convert_env("YES", bool) is True

    assert Variable.convert_env("0", bool) is False
    assert Variable.convert_env("oFf", bool) is False
    assert Variable.convert_env("NO", bool) is False
    assert Variable.convert_env("FAlse", bool) is False
    assert Variable.convert_env("disable", bool) is False


def test_variable_convert_env_number():
    assert Variable.convert_env("1", int) == 1
    assert Variable.convert_env("-0.2", float) == float("-0.2")


def test_variable_convert_env_list_str():
    assert Variable.convert_env("1,2", list[str]) == ["1", "2"]
    assert Variable.convert_env("3", list) == ["3"]
    assert Variable.convert_env("", list) == []
    assert Variable.convert_env(",,,,", list[str]) == ["", "", "", "", ""]


@pytest.mark.xfail(reason="strict tuples are not yet implemented")
def test_variable_convert_env_tuple_str():
    # tuple bug: https://github.com/python/mypy/issues/11098
    assert Variable.convert_env("1,2", tuple[str, str]) == ["1", "2"]  # type: ignore[misc]
    assert Variable.convert_env("", tuple) == []
    assert Variable.convert_env(",,,,", tuple[str, str, str, str]) == ["", "", "", "", ""]  # type: ignore[misc]

    with pytest.raises(ValueError):
        Variable.convert_env("3,4,5", tuple[str])


@pytest.mark.xfail(reason="non str iterables are not yet implemented")
def test_variable_convert_env_list_non_str():
    assert Variable.convert_env("1,2", list[int]) == [1, 2]
    assert Variable.convert_env("3", tuple[int]) == [3]


def test_variable_convert_non_env_invalid():
    with pytest.raises(VariableInvalid):
        Variable.convert_non_env("definitely not int", int)


def test_variable_convert_non_env_already_converted():
    sentinel = object()

    # object errors when called with argument
    assert Variable.convert_non_env(sentinel, object) == sentinel


def test_variable_convert_non_env_optional():
    type_ = Optional[int]

    assert Variable.convert_non_env(None, type_) is None
    assert Variable.convert_non_env("1", type_) == 1


def test_variable_convert_non_env_union():
    # these are actually different types
    assert Variable.convert_non_env("0.0", int | float) == float("0.0")
    assert Variable.convert_non_env("0.0", Union[int, float]) == float("0.0")


def test_variable_convert_non_env_no_valid_options():
    with pytest.raises(VariableInvalid, match="convert to any of union types"):
        Variable.convert_non_env("test", int | float)


def test_variable_fetch_prefers_nothing_over_segfault():
    var = Variable()

    with pytest.raises(VariableMissing):
        var.fetch_value("nonexistent", {}, {})


def test_variable_fetch_prefers_default_over_nothing():
    var = Variable(42)

    value, from_env = var.fetch_value("spameggs", {}, {})

    assert from_env is False
    assert value == 42


@mock.patch.dict(os.environ, {"FOO": "43"})
def test_variable_fetch_prefers_env_over_default():
    var = Variable(42)

    value, from_env = var.fetch_value("FOO", {}, {})

    assert from_env is True
    assert value == "43"


@mock.patch.dict(os.environ, {"FOO": "42"})
def test_variable_fetch_prefers_config_over_env():
    var = Variable()

    value, from_env = var.fetch_value("FOO", {}, {"FOO": "43"})

    assert from_env is False
    assert value == "43"


def test_variable_fetch_prefers_cli_over_config():
    var = Variable()

    value, from_env = var.fetch_value("foo", {"foo": "43"}, {"foo": "42"})

    assert from_env is False
    assert value == "43"


@mock.patch.dict(os.environ, {"FOO": "40"})
def test_variable_fetch_prefers_cli_over_everything():
    var = Variable(41)

    value, from_env = var.fetch_value("foo", {"foo": "42"}, {"FOO": "43"})

    assert from_env is False
    assert value == "42"


def test_variable_resolve_expects_default_or_type():
    var = Variable()

    with pytest.raises(TypeAnnotationNeeded):
        var.resolve("name", {}, {})


def test_variable_resolve_adds_more_context_to_errors():
    name = "var_name"
    var = Variable()

    extra_info = rf"^\[{var.env_name(name)} / {name}\] "

    with pytest.raises(TypeAnnotationNeeded, match=extra_info):
        var.resolve(name, {}, {})

    with pytest.raises(VariableMissing, match=extra_info):
        var.resolve(name, {}, {}, int)

    with pytest.raises(VariableInvalid, match=extra_info):
        var.resolve(name, {name: "not int"}, {}, int)


def test_variable_resolve_prefers_its_own_type():
    var = Variable("1", type_=int)

    assert var.resolve("var", {}, {"var": "2"}, float) == 2


def test_variable_resolve_gets_type_from_default():
    var = Variable(1)

    assert var.resolve("name", {"name": "2"}, {}) == 2


@mock.patch.dict(os.environ, {"FOO": "42"})
def test_variable_resolve_gets_resolves_env():
    var = Variable()

    assert var.resolve("foo", {}, {}, int) == 42


def test_variable_resolve_resolves_config():
    var = Variable()

    assert var.resolve("foo", {}, {"foo": "42"}, int) == 42


def test_variable_resolve_resolves_args():
    var = Variable()

    assert var.resolve("foo", {"foo": "42"}, {}, int) == 42


def test_variable_resolve_env_not_trying_to_parse_default():
    var = Variable("1,2")

    assert var.resolve("foo", {}, {}, list[str]) == ["1", ",", "2"]


@mock.patch.dict(os.environ, {"foo_lowercase": "42"})
def test_variable_resolve_env_overwrite():
    var = Variable(env="foo_lowercase")

    assert var.resolve("foo_lowercase", {}, {}, int) == 42


def test_variable_resolve_config_overwrite():
    var = Variable(config="bar")

    assert var.resolve("something else", {}, {"bar": "42"}, int) == 42


def test_variable_resolve_cli_overwrite():
    var = Variable(arg="baz")

    assert var.resolve("something else", {"baz": "42"}, {}, int) == 42


def test_variable_resolve_sets_env():
    var = Variable(type_=int, set_env=True)

    var.resolve("foo-bar", {}, {"foo-bar": 444})

    assert os.environ["FOO_BAR"] == "444"


def test_variable_resolve_sets_env_with_overwrite():
    var = Variable(env="idk", set_env=True)

    var.resolve("foo-bar-baz", {}, {"foo-bar-baz": 7777}, int)

    assert os.environ["idk"] == "7777"


def test_variable_resolve_does_not_set_env():
    var = Variable(type_=int, set_env=False)

    var.resolve("SPAM_EGGS", {}, {"SPAM_EGGS": 444})

    assert "SPAM_EGGS" not in os.environ


@mock.patch.dict(os.environ, {"FUNNY_ENV": "12121"})
def test_variable_resolve_not_touching_original_env():
    var = Variable(1, env="FUNNY_ENV", set_env=False)

    assert var.resolve("funny_env", {}, {}) == 12121
    assert os.environ["FUNNY_ENV"] == "12121"

    var = Variable(1, env="FUNNY_ENV", set_env=True)

    assert var.resolve("funny_env", {}, {}) == 12121
    assert os.environ["FUNNY_ENV"] == "12121"
