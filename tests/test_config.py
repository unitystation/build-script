import unittest
import os
from unittest.mock import patch
from pathlib import Path

from usautobuild.config import Config
from usautobuild.exceptions import MissingRequiredEnv, MissingConfigFile, MissingRequiredConfig


class ConfigTest(unittest.TestCase):
    req_envs = {"CDN_HOST": "host", "CDN_USER": "user",
                "CDN_PASSWORD": "password", "DOCKER_PASSWORD": "password",
                "DOCKER_USERNAME": "username"}

    def test_given_no_req_envs_results_in_exception(self):
        with self.assertRaises(MissingRequiredEnv):
            Config()

    @patch.dict(os.environ, req_envs)
    def test_when_no_config_file_results_in_exception(self):
        with self.assertRaises(MissingConfigFile):
            Config("config.json")

    @patch.dict(os.environ, req_envs)
    def test_given_no_config_results_in_default(self):
        c = Config("../config.json")
        self.assertEqual(c.git_url, "https://github.com/unitystation/unitystation.git")
        self.assertEqual(c.git_branch, "develop")
        self.assertEqual(c.target_platforms, [
            "linuxserver",
            "StandaloneWindows64",
            "StandaloneOSX",
            "StandaloneLinux64"
        ], )
        self.assertEqual(c.cdn_download_url, "https://unitystationfile.b-cdn.net/{}/{}/{}.zip")
        self.assertEqual(c.forkname, "UnityStationDevelop")
        self.assertEqual(c.output_dir, Path("builds"))
        self.assertEqual(c.abort_on_build_fail, True)


if __name__ == '__main__':
    unittest.main()
