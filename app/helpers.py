# System imports
import os
import ntpath
from retry import retry
from shutil import copy2, move
import xml.etree.ElementTree as ET
from pathlib import Path

# External imports
import exiftool
from PIL import Image
import pygfried


def cmd_is_executable(cmd):
    """Check if command executable.

    Params:
        cmd: filepath to an executable.

    Returns:
        True if the command exists (including if it is on the PATH) and can be
        executed
    """
    if os.path.isabs(cmd):
        paths = [""]
    else:
        paths = [""] + os.environ["PATH"].split(os.pathsep)
    cmd_paths = [os.path.join(path, cmd) for path in paths]
    return any(
        os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK)
        for cmd_path in cmd_paths
    )


def get_path_leaf(path) -> str:
    """Get leaf of given path.

    Params:
        path: path to file

    Returns:
        leaf: string
    """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def get_file_name_without_extension(file_path) -> str:
    """Get name of file without its extension.

    Params:
        file_path: path to file

    Returns:
        name: string
    """
    file_name = get_path_leaf(file_path)
    return os.path.splitext(file_name)[0]


def get_file_extension(file_path) -> str:
    """Get extension of file without its name.

    Params:
        file_path: path to file

    Returns:
        extension: string
    """
    file_name = get_path_leaf(file_path)
    return os.path.splitext(file_name)[1]


def copy_file(source):
    """Copy a file to it's current directory.

    Params:
        source: path to file

    Returns:
        copied_file_path: string
    """
    file_name = get_file_name_without_extension(source)
    extension = get_file_extension(source)
    directory_path = source.split(file_name)[0]

    copied_file_path = f"{directory_path}{file_name}-copy{extension}"
    copy2(source, copied_file_path)

    return copied_file_path


def rename_file(current_file_path, new_file_name) -> str:
    """Rename a file.

    Returns:
        new_file: string
    """
    file_name = get_path_leaf(current_file_path)
    directory_path = current_file_path.split(file_name)[0]

    old_file = os.path.join(directory_path, file_name)
    new_file = os.path.join(directory_path, new_file_name)
    os.rename(old_file, new_file)

    return new_file


def get_icc(file_path):
    """Get icc_profile from image.

    Returns:
        icc information
    """
    img = Image.open(file_path)
    icc = img.info.get("icc_profile")
    img.close()
    return icc


def get_image_dimensions(file_path):
    """Get width and height from image

    Returns:
        (width, height): tuple<int, int>
    """
    image = Image.open(file_path)
    return (image.width, image.height)


def get_resize_params(width, height, max_dimensions=None):
    """
    Calculate new image size, retaining the original aspect ratio (width/height).
    If max_dimensions is specified, the new dimensions will be calculated based on the longest side.
    Otherwise, calculations are based on the width of the image.
    If the width is > 15000 px, the new width will be set to 10000.
    If the width > 5000 px and < 15000 px, the new width will be 5000 + 1/2 width.
    If the width < 5000 px, the new width will be the same as the original width.

    Params:
        width: width of the image
        height: height of the image

    Returns:
        (width, height): tuple<int, int>
    """
    ratio = width / height

    if max_dimensions is not None:
        new_width, new_height = max_dimensions
        if width > height:
            new_height = int(round(new_width / ratio))
        else:
            new_width = int(round(new_height * ratio))
        return (int(round(new_width)), int(round(new_height)))

    new_width = width
    new_height = height

    if width > 15000:
        new_width = 10000
    elif width > 5000:
        new_width = 5000 + (width - 5000) / 2

    new_height = new_width / ratio

    return (int(round(new_width)), int(round(new_height)))


def get_metadata_from_image(file_path):
    """Get all metadata from an image.

    Params:
        file_path: path to file

    Returns:
        metadata: dict containing all metadata
    """
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(file_path)
        return metadata


def copy_metadata(source, destination):
    """Copy metadata from 1 file to another.

    Params:
        source: path to source file
        destination: path to destination file
    """
    source_bytes = bytes(source, "utf-8")
    destination_bytes = bytes(destination, "utf-8")

    with exiftool.ExifTool() as et:
        et.execute(b"-tagsFromFile", source_bytes, destination_bytes)


def remove_file(file_path):
    """Remove a file.

    Params:
        file_path: path to file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print(f"The file {file_path} does not exist")


@retry(tries=5, delay=1, backoff=2)
def move_file(source, destination):
    """Move file from source to destination.

    Params:
        source: path to source file
        destination: path to destination file
    """
    print(source)
    print(destination)
    if os.path.exists(source):
        move(source, destination)
    else:
        print(f"The source file {source} does not exist")


def get_iiif_file_destination(essence_file_path, sidecar_file_path, visibility):
    """Determine the destination location of a IIIF image file.
    The destination is constructed as following:
    - base folder
    - subfolder: public or restricted
    - subfolder: OR-ID
    - subfolder: first 2 characters of the filename
    - essence_file_name: fragment id of the IIIF image file

    Params:
        essence_file_path: absolute path to essence file
        sidecar_file_path: absolute path to xml file containing metadata about the essence file

    Returns:
        destination: path to destination
    """

    tree = ET.parse(sidecar_file_path)
    root = tree.getroot()

    image_base_folder = "/export/images/"
    or_id = root.find(".//CP_id").text
    essence_file_name = root.find(".//FragmentId").text
    characters = essence_file_name[:2]

    destination = (
        image_base_folder
        + visibility
        + "/"
        + or_id
        + "/"
        + characters
        + "/"
        + essence_file_name
        + ".jp2"
    )

    return destination


def check_pronom_id(file_path, expected_pronom_id):
    """Check if a file has the expected pronom id
    More info about pronom: https://www.nationalarchives.gov.uk/pronom/

    Params:
        filename: absolute path to file
        expected_pronom_id: pronom id (e.g. 'fmt/1776')

    Returns:
        pronom_id == expected_pronom_id: boolean
    """
    pronom_id = pygfried.identify(file_path)
    return pronom_id == expected_pronom_id

def get_profile(file_path) -> str:
    """Extract profile name from file_path. Files will be exported to <visibility>/<profile_name>/<pid>.<extension>

    Args:
        file_path (str): <visibility>/<profile_name>/<pid>.<extension>
    """
    return Path(file_path).parent.stem