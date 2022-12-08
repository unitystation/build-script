from typing import Any

from usautobuild.action import Action
from usautobuild.config import Config

__all__ = ("USAction",)


class USAction(Action):
    """Some helpful common defaults for base Action"""

    def __init__(self, config: Config, **kwargs: Any) -> None:
        kwargs.setdefault("jobs", config.jobs)
        kwargs.setdefault("dry_run", config.dry_run)

        super().__init__(**kwargs)

        self.config = config
