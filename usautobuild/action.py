from __future__ import annotations

import concurrent.futures
import inspect
import threading
import time

from collections.abc import Callable, Collection
from typing import Any, Protocol

from usautobuild.config import Config


# NOTE: generic version does not work due to mypy's poor Protocol support
# https://github.com/python/mypy/issues/12595
# https://github.com/python/mypy/issues/13107
class Step(Protocol):
    __step_depends__: Collection[Step]
    __step_dry__: bool

    @staticmethod
    def __call__(self: Action, __ctx: Context) -> Any:
        ...


def step(depends: Collection[Step] = (), dry: bool = False) -> Callable[[Callable[..., Any]], Step]:
    def inner(fn: Callable[..., Any]) -> Step:
        fn_step: Step = fn  # type: ignore[assignment]

        fn_step.__step_depends__ = depends
        fn_step.__step_dry__ = dry

        return fn_step

    return inner


class Action:
    def __init__(self) -> None:
        # self.config = config

        self._steps: list[Step] = []
        self._results: dict[Step, Any] = {}
        self._dependencies: dict[Step, set[Step]] = {}

        self._collect_steps()

        self.__task_completed = threading.Condition()

    def _collect_steps(self) -> None:
        for _, value in inspect.getmembers(type(self)):
            if not hasattr(value, "__step_depends__"):
                continue

            step: Step = value

            self._steps.append(step)
            self._dependencies[step] = set(step.__step_depends__)

    def run(self) -> None:
        # max_workers=self.confing.jobs
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            while True:
                print("deps", self._dependencies)
                if not self._dependencies:
                    break

                ready_deps = [s for s, deps in self._dependencies.items() if not deps]
                for dep in ready_deps:
                    del self._dependencies[dep]

                for step in ready_deps:
                    executor.submit(self.run_step, step)

                print("waiting")
                with self.__task_completed:
                    self.__task_completed.wait()
                print("waited")

                for step in self._results:
                    if (depends := self._dependencies.get(step)) is not None:
                        depends.remove(step)

    def run_step(self, step: Step) -> None:
        print("run_step enter", step)
        ctx = Context(self, step)

        # TODO: exception handling with abort on fail configuration
        result = step(self, ctx)
        print("run_step done")

        self._results[step] = result

        with self.__task_completed:
            self.__task_completed.notify()


class Context:
    __slots__ = (
        "action",
        "step",
    )

    def __init__(self, action: Action, step: Step):
        self.action = action
        self.step = step

    def __getitem__(self, index: Step) -> Any:
        return self.action._results[index]


class Test(Action):
    def aaa(self) -> None:
        ...

    @step()
    def foo(self, ctx: Context) -> None:
        print(ctx.step, "pre sleep")
        time.sleep(2)
        print(ctx.step, "post sleep")

    @step(depends=[foo])
    def bar(self, ctx: Context) -> None:
        print(self.foo)
        print(ctx)
        print(ctx[self.foo])

        print(ctx.step, "pre sleep")
        time.sleep(3)
        print(ctx.step, "pre sleep")


t = Test()
t.run()
print(t._results)
