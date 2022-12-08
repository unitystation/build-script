from __future__ import annotations

import concurrent.futures
import copy
import inspect
import logging

from collections.abc import Callable, Collection
from typing import Any, Optional, Protocol, TypeVar

__all__ = (
    "step",
    "Action",
    "Context",
)

log = logging.getLogger(__name__)


# NOTE: proper generic version with ParamSpec does not work due to mypy's poor Protocol support.
#       T_co / P emits [<nothing>, <nothing>] garbage
#       - https://github.com/python/mypy/issues/12595
#       - https://github.com/python/mypy/issues/13107
#       - https://github.com/python/mypy/issues/13250
#       - https://github.com/python/mypy/issues/13881
class Step(Protocol):
    __step_depends__: set[Step]
    __step_is_dry__: bool

    @staticmethod
    def __call__(self: Action, __ctx: Context) -> Any:
        ...


T = TypeVar("T")
_StepPreWrap = Callable[[T, "Context"], Any]


def step(depends: Collection[Step] = (), dry: bool = False) -> Callable[[_StepPreWrap[T]], Step]:
    def inner(fn: _StepPreWrap[T]) -> Step:
        fn_step: Step = fn  # type: ignore[assignment]

        fn_step.__step_depends__ = set(depends)
        fn_step.__step_is_dry__ = dry

        return fn_step

    return inner


class Action:
    __slots__ = (
        "dry_run",
        "abort_on_failure",
        "_jobs",
        "_steps",
        "_results",
    )

    def __init__(self, jobs: Optional[int] = None, dry_run: bool = False, abort_on_failure: bool = True) -> None:
        self.dry_run = dry_run
        self.abort_on_failure = abort_on_failure
        self._jobs = jobs

        self._steps: dict[Step, set[Step]] = {}
        self._results: dict[Step, Any] = {}

        self._collect_steps()

    def _collect_steps(self) -> None:
        for _, value in inspect.getmembers(type(self)):
            if not hasattr(value, "__step_depends__"):
                continue

            step: Step = value

            self._steps[step] = step.__step_depends__

        # NOTE: if we ever decide to reject wet steps depending on dry steps, do it here

    def run(self) -> None:
        # in case we re-run
        self._results = {}
        # copy because we pop from it
        steps = copy.deepcopy(self._steps)
        # track which steps completed
        futures_to_steps: dict[concurrent.futures.Future[Any], Step] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._jobs) as executor:
            while steps:
                for step in list(steps.keys()):
                    # empty set means last dependency was removed on previous loop iteration
                    if not steps[step]:
                        del steps[step]

                        fut = executor.submit(self._run_step, step)
                        futures_to_steps[fut] = step

                done, _ = concurrent.futures.wait(
                    futures_to_steps.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for fut in done:
                    step = futures_to_steps.pop(fut)
                    try:
                        self._results[step] = fut.result()
                    except Exception:
                        if self.abort_on_failure:
                            raise

                        log.exception("running %s", step)

                        self._results[step] = None

                for deps in steps.values():
                    deps.discard(step)

    def _run_step(self, step: Step) -> Any:
        ctx = Context(self, step)

        if self.dry_run and not step.__step_is_dry__:
            log.debug("skipping execution of %s in dry run", step)
            return None

        return step(self, ctx)


class Context:
    __slots__ = (
        "action",
        "step",
    )

    def __init__(self, action: Action, step: Step):
        self.action = action
        self.step = step

    def __getitem__(self, index: Step) -> Any:
        if inspect.ismethod(index):
            index = index.__func__  # type: ignore[assignment]

        return self.action._results[index]
