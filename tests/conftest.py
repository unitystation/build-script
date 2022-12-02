from pathlib import Path

import pytest

from usautobuild.config import Config


@pytest.fixture
def config() -> Config:
    return Config({"config_file": Path(".")})
