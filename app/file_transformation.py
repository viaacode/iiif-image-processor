# System imports
import subprocess
from pathlib import Path

# External imports
from PIL import Image
from viaa.configuration import ConfigParser
from viaa.observability import logging
from wand.image import Image as WandImage

# Internal imports
from .kakadu import Kakadu
from .helpers import get_file_name_without_extension, get_path_leaf

config = ConfigParser()


class FileTransformer:
    def __init__(self, configParser: ConfigParser = None):
        self.config: dict = configParser.app_cfg
        self.kakadu = Kakadu()

    def crop_borders_and_color_charts(self, file_path) -> str:
        """Crop borders and color charts from image.

        Params:
            file_path: path to file

        Returns:
            Path to cropped image.
        """
        file_name = get_path_leaf(file_path)
        export_path = self.config["transform"]["path"]

        # TODO: move colorchecker path to env variables
        subprocess.call(
            "python /opt/iiif-image-processing/colorchecker/detect.py"
            + f" --weights /opt/iiif-image-processing/colorchecker/weights/best.pt --source \
                {file_path} --crop \
                True --project {export_path} --name cropped --exist-ok",
            shell=True,
        )
        return f"{export_path}cropped/{file_name}"

    def resize(self, file_path, resize_params):
        """Resize image to given width and height.

        Params:
            file_path: path to file
            resize_params: (width, height): new dimensions
        """
        image = Image.open(file_path)
        resized_image = image.resize(resize_params)
        resized_image.save(file_path)

    def convert_to_srgb(self, file_path, icc):
        """Convert image to sRGB color space.

        Params:
            file_path: path to output file
            icc: icc of the image
        """
        logger = logging.get_logger("watcher", config)

        # Convert to 8 bit output_profile
        with WandImage(filename=file_path) as i:
            i.transform_colorspace("srgb")
            i.profiles["ICC"] = icc
            i.save(filename=file_path)
            logger.debug("writing to %s", file_path)
            
    def load_profile(self, profile):
        file = Path(f"profiles/{profile}.profile")
        if not file.exists():
            print(f"'{profile}' profile does not exist, using default profile.")
            file = Path(f"profiles/default.profile")

        with file.open('r') as f:
            lines = f.readlines()
            lines = [line.strip() for line in lines]
        return lines

    def encode_image(self, input_file_path, profile) -> str:
        """Encode image to jp2 file using Kakadu.

        Params:
            input_file_path: path to file

        Returns:
            Path to encoded image
        """
        kakadu_options = self.load_profile(profile)

        # Construct path to new image
        file_name = get_file_name_without_extension(input_file_path)
        output_file_path = self.config["transform"]["path"] + "/" + file_name + ".jp2"

        # Encode image using kdu_compress
        self.kakadu.kdu_compress(input_file_path, output_file_path, kakadu_options)

        return output_file_path
