import io
import logging
import selectors
import subprocess
import sys

from typing import Iterator

__all__ = (
    "run_process_shell",
    "iterate_output",
    "get_version",
)

log = logging.getLogger("usautobuild")


def run_process_shell(command: str, stderr_on_failure: bool = False) -> int:
    """A simple helper function to run shell program to completion logging output and returning status"""

    stderr = []

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    ) as cmd:
        for line, is_stdout in iterate_output(cmd):
            if is_stdout:
                log.debug(line)
            else:
                if stderr_on_failure:
                    stderr.append(line)
                else:
                    log.error(line)

    if cmd.returncode:
        for line in stderr:
            log.error(line)

    return cmd.returncode


def iterate_output(cmd: subprocess.Popen[bytes]) -> Iterator[tuple[str, bool]]:
    """
    Iterates process stdout and stderr at the same time yielding lines and is_stdout boolean
    """

    stdout: io.BufferedReader = cmd.stdout  # type: ignore[assignment]
    stderr: io.BufferedReader = cmd.stderr  # type: ignore[assignment]

    # windows does not work with selectors because there are no pipes on windows
    # https://docs.python.org/3/library/select.html
    # emulate old sequential behaviour: all stdout then all stderr
    if sys.platform in ("win32", "cygwin"):
        for win_line in stdout:
            yield win_line.decode(), True

        for win_line in stderr:
            yield win_line.decode(), False

        return

    sel = selectors.DefaultSelector()

    sel.register(stdout, selectors.EVENT_READ)
    sel.register(stderr, selectors.EVENT_READ)

    # list for perfomance reasons (untested), dict makes more sense here
    stream_buffers = ["", ""]

    not_eof = True
    while not_eof:
        for key, _ in sel.select():
            fileobj: io.BufferedReader = key.fileobj  # type: ignore[assignment]

            if not (data := fileobj.read1()):
                not_eof = False
                break

            # yield in the following steps:
            #   - merge buffer with new data
            #   - split data at newlines
            #   - buffer last line (empty string in case of complete line)
            #   - yield everything except buffered last line
            is_stdout = fileobj is stdout
            # TODO: make decode optional?
            lines = (stream_buffers[is_stdout] + data.decode()).split("\n")
            stream_buffers[is_stdout] = lines[-1]

            for line in lines[:-1]:
                yield line, is_stdout

    # force flush buffers
    is_stdout = True
    if stream_buffers[is_stdout]:
        yield stream_buffers[is_stdout], is_stdout

    is_stdout = False
    if stream_buffers[is_stdout]:
        yield stream_buffers[is_stdout], is_stdout


def get_version() -> str:
    cmd = subprocess.Popen(
        ("git", "log", "-n", "1", "--pretty=format:%h%d by %aN: %s"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = cmd.communicate()

    if cmd.returncode:
        log.debug("unable to get version: %s", stderr)

        return "i don't even know"

    return stdout
