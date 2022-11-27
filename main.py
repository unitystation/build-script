import argparse

from usautobuild.logger import setup_logger, setup_extra_loggers
from usautobuild.licenser import Licenser
from usautobuild.builder import Builder
from usautobuild.config import Config
from usautobuild.gitter import Gitter
from usautobuild.uploader import Uploader
from usautobuild.dockerizer import Dockerizer
from usautobuild.api_caller import ApiCaller

ap = argparse.ArgumentParser()
ap.add_argument("-b", "--build-number", required=False, help="Force a particular build number")
ap.add_argument("-gl", "--get-license", required=False,
                help="If set to true, it will ignore all other procedure and just create a license file")
ap.add_argument("-f", "--config-file", required=False, help="Path to the config file", default=None)
ap.add_argument("-l", "--log-level", type=str, required=False, help="Log level to run this program", default="INFO")
args = vars(ap.parse_args())


def main():
    setup_logger(args["log_level"])

    config = Config(args
    setup_extra_loggers(config)

    if args.get("get_license", None):
        Licenser(config)
        return

    gitter = Gitter(config)
    builder = Builder(config)
    uploader = Uploader(config)
    dockerizer = Dockerizer(config)

    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    api_caller = ApiCaller(config.changelog_api_url, config.changelog_api_key, config.build_number)
    api_caller.post_new_version()


if __name__ == '__main__':
    main()
