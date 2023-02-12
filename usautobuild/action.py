import functools
import logging

from collections.abc import Callable
from typing import Any, Generic, Optional, ParamSpec, TypeVar

from usautobuild.config import Config

__all__ = (
    "Action",
    "step",
)

log = logging.getLogger(__name__)

P = ParamSpec("P")
# T = TypeVar("T")
R = TypeVar("R")


def step(name: Optional[str] = None, dry: bool = False) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def wrapped(fn: Callable[P, R]) -> Callable[P, R]:
        step = Step(fn, name=name, dry=dry)

        return functools.wraps(step)  # type: ignore

    return wrapped


class Step(Generic[P, R]):
    __slots__ = (
        "_fn",
        "_dry",
        "_name",
    )

    def __init__(self, fn: Callable[P, R], *, name: Optional[str], dry: bool):
        self._fn = fn

        self._name = fn.__name__ if name is None else name
        self._dry = dry

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self._fn(*args, **kwargs)

    def __str__(self) -> str:
        return self._name

    @property
    def is_dry(self) -> bool:
        return self._dry


# TODO: metaclass steps registration


class Action:
    __slots__ = (
        "config",
        "_steps",
    )

    def __init__(self, config: Config):
        self.config = config
        self._steps: list[Step[Any, Any]] = []

    def run(self) -> None:
        """Run all steps in action"""

        log.debug("Starting %s with %d steps", self, len(self._steps))

        for step in self._steps:
            if self.config.dry_run and not step.is_dry:
                log.info("Skipping %s in dry run", step)
                continue

            step()

        log.debug("Completed %s", self)
