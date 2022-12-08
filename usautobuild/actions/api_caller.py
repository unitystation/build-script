from logging import getLogger
from typing import Any

import requests

from usautobuild.action import Context, step

from .action import USAction

log = getLogger("usautobuild")


class APICaller(USAction):
    @step()
    def post_new_version(self, _ctx: Context) -> Any:
        if self.dry_run:
            log.info("Dry run, skipping Changelog API call")
            return

        data = {
            "version_number": str(self.config.build_number),
            "date_created": self.version_to_date(str(self.config.build_number)),
            "secret_token": self.config.changelog_api_key,
        }

        response = requests.post(self.config.changelog_api_url, data=data)
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
