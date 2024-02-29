from collections import defaultdict
from dataclasses import dataclass
from logging import getLogger
from typing import DefaultDict

import requests

from usautobuild.config import Config

log = getLogger("usautobuild")

category_to_emoji = {
    "NEW": ":new:",
    "FIX": ":wrench:",
    "BALANCE": ":scales:",
    "IMPROVEMENT": ":arrow_up:",
}


@dataclass
class ChangeModel:
    author_username: str
    description: str
    pr_url: str
    pr_number: int
    category: str
    build: str
    date_added: str


@dataclass
class Pr:
    pr_number: int
    changes: list[ChangeModel]


@dataclass
class NewestBuildModel:
    build: str
    changes: list[ChangeModel]


def group_changes_by_pr(newest_build: NewestBuildModel) -> list[Pr]:
    pr_changes: DefaultDict[int, list[ChangeModel]] = defaultdict(list)

    for change in newest_build.changes:
        pr_changes[change.pr_number].append(change)

    return [Pr(pr_number, changes) for pr_number, changes in pr_changes.items()]


def format_changelog(prs: list[Pr], build: str) -> str:
    final_string = f"# Build {build}"

    if not prs:
        final_string += "\n\nThis build likely contains only internal changes. See the previous build for changelog."
        return final_string

    for pr in prs:
        final_string += f"\n\n## PR #{pr.pr_number} (<{pr.changes[0].pr_url}>)"
        final_string += f"\nby {pr.changes[0].author_username}\n"

        for change in pr.changes:
            final_string += f"\n{format_change(change)}"
    return final_string


def format_change(change: ChangeModel) -> str:
    emoji = category_to_emoji.get(change.category, ":question:")
    return f"- {emoji} {change.description}"


class DiscordChangelogPoster:
    def __init__(self, config: Config):
        self.changelog_webhook = config.changelog_webhook
        self.newest_build_url = config.newest_build_api_url

    def post_changelog(self, message: str) -> None:
        message_chunks = [message[i : i + 2000] for i in range(0, len(message), 2000)]

        for chunk in message_chunks:
            wh_data = {
                "content": chunk,
                # disallow any pings
                "allowed_mentions": {"parse": []},
            }

            response = requests.post(self.changelog_webhook, json=wh_data, timeout=30)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                log.error("Failed to post new build to the changelog webhook. See console for more information.")
                log.error("%s", e, extra={"discord": False})
                log.error(response.json())
                raise

    def fetch_newest_build(self) -> NewestBuildModel:
        resp = requests.get(self.newest_build_url, timeout=30)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            log.error("Failed to fetch newest build from API: %s", e)
            log.error(resp.json())
            raise

        data = resp.json()
        return NewestBuildModel(
            build=data["build"],
            changes=[
                ChangeModel(
                    author_username=change["author_username"],
                    description=change["description"],
                    pr_url=change["pr_url"],
                    pr_number=int(change["pr_number"]),
                    category=change["category"],
                    build=change["build"],
                    date_added=change["date_added"],
                )
                for change in data["changes"]
            ],
        )

    def start_posting(self) -> None:
        log.info("Starting changelog posting")
        newest_build = self.fetch_newest_build()
        prs = group_changes_by_pr(newest_build)
        message = format_changelog(prs, newest_build.build)
        self.post_changelog(message)
