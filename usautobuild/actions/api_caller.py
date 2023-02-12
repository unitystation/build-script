from logging import getLogger

import requests

from usautobuild.action import Action, step

log = getLogger("usautobuild")


class ApiCaller(Action):
    @step()
    def post_new_version(self) -> None:
        if self.config.dry_run:
            log.info("Dry run, skipping Changelog API call")
            return

        build_number = str(self.config.build_number)

        data = {
            "version_number": build_number,
            "date_created": self.version_to_date(build_number),
            "secret_token": self.config.changelog_api_key,
        }

        response = requests.post(self.config.changelog_api_url, data=data)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error("Failed to post new version to changelog api: %s", e)
            log.error(response.json())
            raise

    @staticmethod
    def version_to_date(version: str) -> str:
        year = version[0:2]
        month = version[2:4]
        day = version[4:6]

        return f"20{year:0>2}-{month:0>2}-{day:0>2}"
