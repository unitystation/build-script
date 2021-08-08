import argparse

from usautobuild.logger import create_logger
from usautobuild.licenser import Licenser
from usautobuild.builder import Builder
from usautobuild.config import Config
from usautobuild.gitter import Gitter
from usautobuild.uploader import Uploader

ap = argparse.ArgumentParser()
ap.add_argument("-g", "--get-license", required=False,
                help="If set to true, it will ignore all other procedure and just create a license file")
ap.add_argument("-c", "--config-file", required=False, help="Path to the config file")
ap.add_argument("-l", "--log-level", required=False, help="Log level to run this program")
args = vars(ap.parse_args())


def main():
    config_file = args.get("config_file", None)
    config = Config(config_file)
    logger = create_logger(args.get("log_level", "INFO"), config)

    if args.get("get_license", None):
        Licenser(config, logger)
        return

    gitter = Gitter(config, logger)
    builder = Builder(config, logger)
    uploader = Uploader(config, logger)

    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()


if __name__ == '__main__':
    main()
