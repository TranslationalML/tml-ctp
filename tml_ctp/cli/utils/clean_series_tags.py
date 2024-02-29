#!/usr/bin/env python3

# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to clean tags at all levels in DICOM data."""

import numpy as np
import pandas as pd
from os.path import join
import os
import pydicom
import argparse


def find_ref_image(root_dir: str):
    """
    Traverse directories starting from the given root folder and return
    the full path of the first file encountered.

    Args:
        root_dir (str): Path to the root directory from which to start the traversal.

    Returns:
        str: Full path to the first file encountered or None if no files are found.
    """

    for dirpath, dirnames, filenames in os.walk(root_dir):
        if filenames:  # If there are files in the current directory
            return os.path.join(dirpath, filenames[0])
    return None


def get_dangerous_tag_pairs(original_subject_folder: str, ctp_subject_folder: str):
    """
    Extract potentially sensitive tag pairs from the reference DICOM images
    in both the original and CTP subject folders.

    The function tries to read the first DICOM image from both directories
    and extracts the PatientID and SeriesDate tags.

    Args:
        original_subject_folder (str): Path to the original subject's directory.
        ctp_subject_folder (str): Path to the CTP subject's directory.

    Returns:
        list: A list of sensitive tag pairs, or an empty list if an error occurs.
    """
    sensible_tag_pairs = []
    try:
        original_ref_file = find_ref_image(original_subject_folder)
        ctp_ref_file = find_ref_image(ctp_subject_folder)

        original_ref_image = pydicom.dcmread(original_ref_file)
        ctp_ref_image = pydicom.dcmread(ctp_ref_file)

        sensible_tag_pairs.append(
            [original_ref_image.PatientID, ctp_ref_image.PatientID]
        )
        sensible_tag_pairs.append(
            [original_ref_image.SeriesDate, ctp_ref_image.SeriesDate]
        )

    except:
        sensible_tag_pairs = []

    list_issues = []
    if sensible_tag_pairs == []:
        try:
            _ = original_ref_image.PatientID
        except:
            list_issues.append("original_ref_image.PatientID")
        try:
            _ = ctp_ref_image.PatientID
        except:
            list_issues.append("ctp_ref_image.PatientID")

        try:
            _ = original_ref_image.SeriesDate
        except:
            list_issues.append("original_ref_image.SeriesDate")
        try:
            _ = ctp_ref_image.SeriesDate
        except:
            list_issues.append("ctp_ref_image.SeriesDate")

    return sensible_tag_pairs, list_issues


def replace_str_in_number(elem_value, initial_str: str, new_str: str):
    """Function to replace a string in a number.

    Args:
        elem_value: Data element value in which to replace the string
        initial_str (str): Initial string to be replaced
        new_str (str): New string to replace the initial string

    Returns:
        int or float: Number with the replaced string
    """
    # Save the type of the element value
    elem_value_type = type(elem_value)
    # Convert the element value to a string
    elem_value_str = str(elem_value)
    # Replace the initial string with the new string and convert back
    # to the original type
    return elem_value_type(elem_value_str.replace(initial_str, new_str))


def replace_substr_in_tag(
    elem_value: str,
    sensible_string: str,
    replace_string: str,
    tag_string: str,
    new_string: str,
):
    """Function to replace a substring within a tag if the tag contains a "sensitive" string.

    Args:
        elem_value (str): Data element value in which to search and replace the string.
        sensible_string (str): Sensitive string to search within the tag (taken from the original cohort).
        replace_string (str): String to replace the sensible_string (new tag taken from the uuid generator, file name, or the new dates, etc).
        tag_string (str): The tag within which to search for the sensible_string.
        new_string (str): New value to use if the tag contains the sensible_string.

    Returns:
        str: Modified string based on the presence of sensible_string in tag_string.
    """

    # Convert the elem_value to string to work with it
    elem_value_str = str(elem_value)

    # Check if tag_string contains the sensible_string
    if sensible_string in elem_value_str[elem_value_str.find(tag_string) :]:
        # Replace new_string with replace_string
        modified_new_string = new_string.replace(sensible_string, replace_string)
        # Replace tag_string in elem_value with modified_new_string
        elem_value_str = elem_value_str.replace(tag_string, modified_new_string)

    return elem_value_str


# Example usage
# This will search for '<tag>some sensitive info</tag>' and if it finds 'sensitive',
# it will replace the tag with 'This is a <replaced> secret </replaced>'
# print(replace_substr_in_tag('<tag>some sensitive info</tag>', 'sensitive', 'replaced', '<tag>', 'This is a <replaced> secret </replaced>'))


def anonymize_tag_recurse(ds: pydicom.Dataset, initial_str: str, new_str: str):
    """Function to anonymize / replace first level and nested tags in a pydicom Dataset recursively.

    It handles the cases where the value of the data element is one of the following:
    a single string value, a number, a list or tuple with all strings or all numbers,
    or a multi-value string with backslash separator.

    Args:
        ds : pydicom Dataset to anonymize
        initial_str : Initial string to be replaced
        new_str : New string to replace the initial string

    Returns:
        ds : Pydicom Dataset with the replaced tag values
    """
    for elem in ds:
        if elem.VR == "SQ":
            [anonymize_tag_recurse(item, initial_str, new_str) for item in elem.value]
        else:
            if isinstance(elem.value, str):
                if "\\" in elem.value:
                    elem.value = "\\".join(
                        [
                            value.replace(initial_str, new_str)
                            for value in elem.value.split("\\")
                        ]
                    )
                else:
                    elem.value = elem.value.replace(initial_str, new_str)
            elif isinstance(elem.value, pydicom.tag.BaseTag):
                # Handle case when the value of a tag is a tag e.g. '(0020, 9056)'.
                # Otherwise it is seen as int or float and raises an error.
                pass
            elif isinstance(elem.value, int) or isinstance(elem.value, float):
                if initial_str.isnumeric():
                    elem.value = replace_str_in_number(elem.value, initial_str, new_str)
            elif isinstance(elem.value, list) or isinstance(elem.value, tuple):
                for i, value in enumerate(elem.value):
                    if isinstance(value, str):
                        elem.value[i] = value.replace(initial_str, new_str)
                    elif isinstance(elem.value, int) or isinstance(elem.value, float):
                        if initial_str.isnumeric():
                            elem.value = replace_str_in_number(
                                elem.value, initial_str, new_str
                            )
    return ds


def get_parser():
    """Get parser object for script `clean_series_tags.py`."""
    parser = argparse.ArgumentParser(
        description="Dangerous tags process and recursive overwrite of DICOM images."
    )
    parser.add_argument(
        "--CTP_data_folder", type=str, help="Path to the CTP data folder."
    )
    parser.add_argument(
        "--original_cohort", type=str, help="Path to the original cohort folder."
    )
    parser.add_argument(
        "--ids_file",
        type=str,
        help="Path to the IDs file generated byt the CTP batcher file.",
    )
    return parser


def main():
    """Main function of the `clean_series_tags.py` script."""
    # Parse command-line arguments
    parser = get_parser()
    args = parser.parse_args()

    CTP_data_folder = args.CTP_data_folder
    original_cohort = args.original_cohort
    ids_file = args.ids_file

    # Check if the CTP_data_folder exists
    if not os.path.isdir(CTP_data_folder):
        raise NotADirectoryError(f"{CTP_data_folder} is not a directory")

    # Check if the original_cohort exists
    if not os.path.isdir(original_cohort):
        raise NotADirectoryError(f"{original_cohort} is not a directory")

    # Check if the ids_file exists
    if not os.path.isfile(ids_file):
        raise FileNotFoundError(f"{ids_file} is not a file")

    # Load the IDs file
    ids_pairs = pd.read_csv(
        ids_file,
        delimiter=",",
        skipinitialspace=True,
        dtype=str,
        header=None
    ).to_numpy(dtype=str)
    # ids_pairs = np.genfromtxt(ids_file, delimiter=', ', dtype=str)

    # [Patch] just to be able to handle single folder cases inside the ids_file
    if not isinstance(ids_pairs[0], np.ndarray):
        ids_pairs = np.array([ids_pairs])

    for idx, pair in enumerate(ids_pairs):
        print(idx, len(ids_pairs))

        original_subject_folder = join(original_cohort, pair[0])
        ctp_subject_folder = join(CTP_data_folder, pair[1])

        # [Todo] needs an exception when it can't find the pair of tags
        dangerous_tag_pairs, list_issues = get_dangerous_tag_pairs(
            original_subject_folder, ctp_subject_folder
        )
        print(dangerous_tag_pairs)

        if len(list_issues) > 0:
            log_file = join(CTP_data_folder, "all_file_issues.txt")
            with open(log_file, "a") as file:
                file.write(f"{pair[0]} {pair[1]} {list_issues} \n")
            file.close()

        for dirpath, _, filenames in os.walk(ctp_subject_folder):
            print(f"> Clean {dirpath}")
            for filename in filenames:
                ctp_file_path = join(dirpath, filename)
                ctp_file_image = pydicom.dcmread(ctp_file_path)
                ctp_dicom_corrected = ctp_file_image  # not necessary, just for clarity

                for dangerous_tag in dangerous_tag_pairs:
                    ctp_dicom_corrected = anonymize_tag_recurse(
                        ctp_dicom_corrected, dangerous_tag[0], dangerous_tag[1]
                    )

                ctp_dicom_corrected.save_as(ctp_file_path)  # No turning back
    print("Done!")


if __name__ == "__main__":
    main()
