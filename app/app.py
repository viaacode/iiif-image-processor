
# System imports
import subprocess
import zipfile
import shutil
from pathlib import Path
from os import walk, environ

# Internal imports
from viaa.configuration import ConfigParser
from viaa.observability import logging

# External imports
import inotify.adapters

from app.helpers import get_iiif_file_destination, check_pronom_id


APP_NAME = "iiif-image-processor"

FOLDER_TO_WATCH = "/export/home/viaa/pub"
WORKFOLDER_BASE = "/opt/image-processing-workfolder"

class Watcher:
    def __init__(self):
        config_parser = ConfigParser()
        self.log = logging.get_logger(__name__, config=config_parser)
        self.config = config_parser.app_cfg

        # Topics
        self.app_config = self.config["mh-sip-creator"]
        self.consumer_topic = self.app_config["consumer_topic"]

    def unzip_incoming_zip_to_workfolder(self) -> tuple[str, str]:
        # Unzips incoming zips from `FOLDER_TO_WATCH` in `WORKFOLDER`
        # Returns path to esssence and sidecar as a tuple
        return ("", "")
        pass
    
    def main(self) -> None:
        i = inotify.adapters.InotifyTree(FOLDER_TO_WATCH)
        self.log.info(f"Watching directory: '{FOLDER_TO_WATCH}'")

        for event in i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event # type: ignore

            # TODO: add mask to inotify
            # Only listen to write events
            if "IN_CLOSE_WRITE" not in type_names:
                continue

            # Only look at zip files
            if not filename.endswith(".zip"):
                print(f"Ignoring file {filename}")
                continue

            # Unpack zip to working directory
            full_file_path = path + "/" + filename
            workfolder = WORKFOLDER_BASE + "/" + Path(full_file_path).stem

            self.log.debug("Received event for %s", full_file_path)

            try:
                with zipfile.ZipFile(full_file_path, "r") as zip_ref:
                    zip_ref.extractall(workfolder)
            except zipfile.BadZipFile:
                self.log.debug("Invalid zip file %s", full_file_path)
                continue

            essence_files_in_workfolder = [
                file
                for file in next(walk(workfolder), (None, None, []))[2]
                if check_pronom_id(
                    workfolder + "/" + file, "fmt/353"
                )  # Tagged Image File Format (tif)
            ]
            file_to_transform = essence_files_in_workfolder[0]

            metadata_files_in_workfolder = [
                file
                for file in next(walk(workfolder), (None, None, []))[2]
                if check_pronom_id(
                    workfolder + "/" + file, "fmt/101"
                )  # Extensible Markup Language (xml)
            ]
            file_to_transform_path = workfolder + "/" + file_to_transform
            sidecar_path = workfolder + "/" + metadata_files_in_workfolder[0]

            # Calculate visibilty
            visibility = "public" if "public" in path else "restricted"

            destination = get_iiif_file_destination(
                file_to_transform_path, sidecar_path, visibility
            )

            my_env = environ.copy()
            my_env["PATH"] = f"/opt/iiif-image-processing/env/bin:{my_env['PATH']}"

            self.log.debug("Running transform_file for %s", file_to_transform_path)
            self.log.debug("Destination %s", destination)

            # Transform image by executing scripts
            subprocess.run(
                "python3 /opt/iiif-image-processing/transform_file.py"
                + f" --file_path {file_to_transform_path}"
                + f" --destination {destination}",
                shell=True,
                check=True,
                env=my_env,
            )

            # Remove temporary files and folders
            self.log.debug("Removing zip file %s", full_file_path)
            Path(full_file_path).unlink(missing_ok=True)

            try:
                self.log.debug("Removing workfolder %s", workfolder)
                shutil.rmtree(workfolder)
            except OSError:
                self.log.debug("Error removing workfolder %s", workfolder)
