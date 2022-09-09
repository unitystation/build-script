import argparse

from usautobuild.logger import setup_logger
from usautobuild.licenser import Licenser
from usautobuild.discord import Discord
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
ap.add_argument("-f", "--config-file", required=False, help="Path to the config file")
ap.add_argument("-l", "--log-level", required=False, help="Log level to run this program")
args = vars(ap.parse_args())


def main():
    setup_logger(args.get("log_level", "INFO"))
    config_file = args.get("config_file", None)

    config = Config(args, config_file)

    if args.get("get_license", None):
        Licenser(config)
        return
    Discord(config)
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
