from logging import getLogger

from usautobuild.utils import run_process_shell

log = getLogger("usautobuild")


def tag_as_stable() -> None:
    log.info("Pushing a stable build from the latest build!")

    if status := run_process_shell("docker build -t unitystation/unitystation:stable Docker"):
        raise Exception(f"Build failed: {status}")

    if status := run_process_shell(
        'echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin',
        # complains about storing credentials in filesystem
        stderr_on_failure=True,
    ):
        raise Exception(f"Docker login failed: {status}")

    if status := run_process_shell("docker push unitystation/unitystation:stable"):
        raise Exception(f"Push failed: {status}")
