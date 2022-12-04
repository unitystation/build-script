from logging import getLogger

import requests

from usautobuild.config import Config

log = getLogger("usautobuild")


class ApiCaller:
    def __init__(self, config: Config):
        self.api_url = config.changelog_api_url
        self.api_key = config.changelog_api_key
        self.build_number = config.build_number
        self.dry_run = config.dry_run

    def post_new_version(self) -> None:
        if self.dry_run:
            log.info("Dry run, skipping Changelog API call")
            return

        data = {
            "version_number": str(self.build_number),
            "date_created": self.version_to_date(str(self.build_number)),
            "secret_token": self.api_key,
        }

        response = requests.post(self.api_url, data=data)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(f"Failed to post new version to changelog api: {e}")
            log.error(response.json())
            raise

    @staticmethod
    def version_to_date(version: str) -> str:
        year = version[0:2]
        month = version[2:4]
        day = version[4:6]

        return f"20{year}-{month}-{day}"
