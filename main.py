from usautobuild import builder, uploader, dockerizer, gitter
from os import system

if __name__ == "__main__":
    gitter.start_gitting()
    builder.start_building()
    uploader.start_upload()
    dockerizer.start_dockering()

    system("pause")
