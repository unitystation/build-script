from usautobuild import builder, uploader, dockerizer
from os import system

if __name__ == "__main__":
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    system("pause")
