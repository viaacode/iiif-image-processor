# System imports
import glob, os
import argparse
from pathlib import Path

# External imports
from viaa.observability import logging
from viaa.configuration import ConfigParser

# Internal imports
from app.file_transformation import FileTransformer

# from app.file_validation import FileValidator
from app.helpers import (
    copy_file,
    copy_metadata,
    get_metadata_from_image,
    get_resize_params,
    get_file_extension,
    get_icc,
    get_image_dimensions,
    move_file,
    remove_file,
    rename_file,
)

"""
Script to apply transformations (crop, resize, convert color space, encode,
add metadata) to an image file.
"""

if __name__ == "__main__":
    # Init
    configParser = ConfigParser()
    parser = argparse.ArgumentParser()
    file_transformer = FileTransformer(configParser)
    logger = logging.get_logger("transform_file", configParser)

    # Get arguments
    parser.add_argument(
        "--file_path", type=str, default=None, help="Path to input file", required=True
    )
    parser.add_argument(
        "--destination", type=str, default=None, help="Destination output file", required=False
    )
    parser.add_argument(
        "--max_size", type=str, default=None, help="Max width for the transformed image", required=False
    )
    parser.add_argument(
        "--profile", type=str, default=None, help="Kakadu profile to be used", required=False
    )
    args = parser.parse_args()
    file_path = args.file_path
    destination = args.destination
    max_size = args.max_size
    profile = args.profile

    # Copy file and rename it to external_id.
    # File has to be copied so metadata can be added again later.
    extension = get_file_extension(file_path)
    external_id = Path(file_path).stem
    copied_file_path = copy_file(file_path)
    file_path = rename_file(file_path, external_id + extension)

    # Get metadata from original image
    metadata = get_metadata_from_image(file_path)

    # Get icc from image here, because it will be lost. 
    # The original icc is needed to convert the color space to sRGB.
    icc = get_icc(file_path)

    # Resize file
    width, height = get_image_dimensions(file_path)
    if max_size == "full":
        resize_params = (width, height)
    else:  
        if max_size is not None:
            size_map = {
                "small": 2000,
                "medium": 4500,
                "large": 10000,
            }
            max_dimensions = size_map.get(max_size, None)
        else:
            max_dimensions = None
        resize_params = get_resize_params(width, height, max_dimensions)
    
    file_transformer.resize(file_path, resize_params)

    # Change color space
    file_transformer.convert_to_srgb(file_path, icc)

    # Encode to jp2
    encoded_file = file_transformer.encode_image(file_path, profile)
    logger.debug("Encoded file %s", encoded_file)

    # Add metadata to file
    copy_metadata(copied_file_path, encoded_file)

    # Move file to destination
    if destination is not None:
        logger.debug("Moving encoded_file file %s to %s", encoded_file, destination)
        move_file(encoded_file, destination)
    logger.debug("moved")

    # Cleanup
    remove_file(copied_file_path)
    for f in glob.glob(copied_file_path + '*'):
        os.remove(f)
