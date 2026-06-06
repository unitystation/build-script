import os

from pathlib import Path
from unittest import mock

import pytest

from usautobuild.config import Config


@pytest.fixture
@mock.patch.dict(
    os.environ,
    {
        "R2_ACCOUNT_ID": "account",
        "R2_ACCESS_KEY_ID": "key",
        "R2_SECRET_ACCESS_KEY": "secret",
        "DOCKER_PASSWORD": "password",
        "DOCKER_USERNAME": "username",
        "CHANGELOG_API_URL": "url",
        "CHANGELOG_API_KEY": "key",
    },
    clear=True,
)
def config() -> Config:
    return Config({"config_file": Path()})
