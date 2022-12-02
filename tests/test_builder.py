import datetime

from usautobuild.builder import Builder
from usautobuild.config import Config


def test_produce_build_number(config: Config):
    builder = Builder(config)
    builder.produce_build_number()
    build_number = int(datetime.datetime.now().strftime("%y%m%d%H"))

    assert build_number == config.build_number
