import requests
from logging import getLogger

log = getLogger("usautobuild")


class ApiCaller:
    def __init__(self, api_url: str, api_key: str, build_number: int):
        self.api_url = api_url
        self.api_key = api_key
        self.build_number = build_number

    def post_new_version(self):
        data = {
            "version_number": str(self.build_number),
            "date_created": self.version_to_date(str(self.build_number)),
            "secret_token": self.api_key
        }

        response = requests.post(self.api_url, data=data)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error(f"Failed to post new version to changelog api: {e}")
            log.error(response.json())
            raise

    def version_to_date(self, version: str) -> str:
        year = version[0:2]
        month = version[2:4]
        day = version[4:6]

        return f"20{year}-{month}-{day}"
