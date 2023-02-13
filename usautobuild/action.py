from __future__ import annotations

import logging

from collections.abc import Callable, Collection
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar

if TYPE_CHECKING:
    from typing_extensions import Self

from usautobuild.config import Config

__all__ = (
    "Action",
    "step",
)

log = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def step(dry: bool = False) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for marking action steps"""

    def wrapped(fn: Callable[P, R]) -> Callable[P, R]:
        return Step(fn, dry=dry)

    return wrapped


class Step(Generic[P, R]):
    # injected self argument
    __action__: Action

    __slots__ = (
        "__action__",
        "_fn",
        "_dry",
    )

    def __init__(self, fn: Callable[P, R], *, dry: bool):
        self._fn = fn

        self._dry = dry

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self._fn(self.__action__, *args, **kwargs)  # type: ignore

    def __str__(self) -> str:
        return self._fn.__name__

    @property
    def is_dry(self) -> bool:
        return self._dry


class Action:
    """A sequence of steps grouped into class"""

    __steps__: Collection[Step[Any, Any]]

    __slots__ = (
        "__steps__",
        "config",
    )

    def __new__(cls, *__args: Any, **__kwargs: Any) -> Self:
        self = super().__new__(cls)

        steps = []
        for value in cls.__dict__.values():
            if not isinstance(value, Step):
                continue

            value.__action__ = self
            steps.append(value)

        self.__steps__ = tuple(steps)

        return self

    def __init__(self, config: Config):
        self.config = config

    @classmethod
    def run(cls, config: Config) -> None:
        """Run all steps in action"""

        self = cls(config)

        log.debug("Starting %s with %d steps", cls, len(self.__steps__))

        for step in self.__steps__:
            if self.config.dry_run and not step.is_dry:
                log.info("Skipping %s in dry run", step)
                continue

            step()

        log.debug("Completed %s", self)
