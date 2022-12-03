import datetime

from usautobuild.config import Config


# NOTE: this will fail on very rare occasions at 0:00 of next day
def test_config_build_number(config: Config):
    assert config.build_number == int(datetime.datetime.now().strftime("%y%m%d%H"))
