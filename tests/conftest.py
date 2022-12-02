import os

from pathlib import Path
from unittest import mock

import pytest

from usautobuild.config import Config


@pytest.fixture
@mock.patch.dict(
    os.environ,
    {
        "CDN_HOST": "host",
        "CDN_USER": "user",
        "CDN_PASSWORD": "password",
        "DOCKER_PASSWORD": "password",
        "DOCKER_USERNAME": "username",
        "CHANGELOG_API_URL": "url",
        "CHANGELOG_API_KEY": "key",
    },
    clear=True,
)
def config() -> Config:
    return Config({"config_file": Path(".")})
