# System imports
import os
import subprocess

# Internal imports
from .helpers import cmd_is_executable


class Kakadu:
    """Wrapper around the Kakadu library."""

    def __init__(self):
        if not cmd_is_executable("kdu_compress"):
            raise OSError(
                "Could not find executable kdu_compress. Check kakadu is installed and \
                kdu_compress exists at the configured \
                path")
            

    def kdu_compress(self, input_files, output_file, kakadu_options):
        """Converts an image file supported by kakadu to jpeg2000.
        Bitonal or greyscale image files are converted to a single channel jpeg2000
        file.

        Params:
            input_filepaths: Either a single filepath or a list of filepaths.
            If given three single channel files, Kakadu will combine them into
            a single 3 channel image

            output_filepath:

            kakadu_options: command line arguments

        Raises:
            IOError: if input_file could not be accessed or if writing to output path
            fails
            Exception: if subprocess call fails
        """
        if not isinstance(input_files, list):
            input_files = [input_files]

        # the -i parameter can have multiple files listed
        for input_file in input_files:
            if not os.access(input_file, os.R_OK):
                raise IOError(
                    "Could not access image file {0} to convert".format(input_file)
                )

        if not os.access(os.path.abspath(os.path.dirname(output_file)), os.W_OK):
            raise IOError("Could not write to output path {0}".format(output_file))

        input_option = ",".join(["{0}".format(item) for item in input_files])

        command_options = [
            "kdu_compress",
            "-i",
            input_option,
            "-o",
            output_file,
        ] + kakadu_options

        try:
            return subprocess.check_call(command_options, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception(
                "Kakadu {0} failed on {1}. Command: {2}, Error: {3}".format(
                    "kdu_compress", input_option, " ".join(command_options), e
                )
            )
