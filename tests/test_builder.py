import datetime
import os
import unittest

from unittest.mock import patch

import pytest

from usautobuild.builder import Builder
from usautobuild.config import Config

req_envs = {
    "CDN_HOST": "host",
    "CDN_USER": "user",
    "CDN_PASSWORD": "password",
    "DOCKER_PASSWORD": "password",
    "DOCKER_USERNAME": "username",
}


@pytest.mark.xfail(reason="outdated")
class TestBuilder(unittest.TestCase):
    @patch.dict(os.environ, req_envs)
    def setUp(self) -> None:
        self.config = Config()
        # self.eh = ErrorHandler()

    def test_produce_build_number(self):
        builder = Builder(self.config, self.eh)
        builder.produce_build_number()
        build_number = datetime.datetime.now().strftime("%y%m%d%H")
        self.assertEqual(build_number, self.config.build_number)


if __name__ == "__main__":
    unittest.main()
