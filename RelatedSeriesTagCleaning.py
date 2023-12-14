import numpy as np 
from os.path import join
import os
import pydicom 
import argparse


__authors__ = [ "Jonathan Rafael  Patiño-Lopez","Sebastien no-more-rasta Turbier"]

__status__ = "development"

def find_ref_image(root_dir):

    """
    Traverse directories starting from the given root folder and return 
    the full path of the first file encountered.
    
    Parameters:
    - root_dir (str): Path to the root directory from which to start the traversal.
    
    Returns:
    - str: Full path to the first file encountered or None if no files are found.
    """
        
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if filenames:  # If there are files in the current directory
            return os.path.join(dirpath, filenames[0])
    return None


def get_dangerous_tag_pairs(original_subject_folder,ctp_subject_folder):
    """
    Extract potentially sensitive tag pairs from the reference DICOM images
    in both the original and CTP subject folders.
    
    The function tries to read the first DICOM image from both directories 
    and extracts the PatientID and SeriesDate tags.
    
    Parameters:
    - original_subject_folder (str): Path to the original subject's directory.
    - ctp_subject_folder (str): Path to the CTP subject's directory.
    
    Returns:
    - list: A list of sensitive tag pairs, or an empty list if an error occurs.
    """
    sensible_tag_pairs = []
    try: 
        original_ref_file = find_ref_image(original_subject_folder)
        ctp_ref_file      = find_ref_image(ctp_subject_folder)

        original_ref_image = pydicom.dcmread(original_ref_file)
        ctp_ref_image = pydicom.dcmread(ctp_ref_file)
        sensible_tag_pairs.append([original_ref_image.PatientID, ctp_ref_image.PatientID])

        sensible_tag_pairs.append([original_ref_image.SeriesDate, ctp_ref_image.SeriesDate])

    except:
        return []
    
    return sensible_tag_pairs



def replace_str_in_number(elem_value, initial_str, new_str):
    """Function to replace a string in a number.

    Args:
        elem_value : Data element value in which to replace the string
        initial_str : Initial string to be replaced
        new_str : New string to replace the initial string

    Returns:
        number: Number with the replaced string
    """
    # Save the type of the element value
    elem_value_type = type(elem_value)
    # Convert the element value to a string
    elem_value_str = str(elem_value)
    # Replace the initial string with the new string and convert back
    # to the original type
    return elem_value_type(elem_value_str.replace(initial_str, new_str))


def replace_substr_in_tag(elem_value, sensible_string, replace_string, tag_string, new_string):
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
    if sensible_string in elem_value_str[elem_value_str.find(tag_string):]:
        # Replace new_string with replace_string
        modified_new_string = new_string.replace(sensible_string, replace_string)
        # Replace tag_string in elem_value with modified_new_string
        elem_value_str = elem_value_str.replace(tag_string, modified_new_string)

    return elem_value_str

# Example usage
# This will search for '<tag>some sensitive info</tag>' and if it finds 'sensitive',
# it will replace the tag with 'This is a <replaced> secret </replaced>'
# print(replace_substr_in_tag('<tag>some sensitive info</tag>', 'sensitive', 'replaced', '<tag>', 'This is a <replaced> secret </replaced>'))

def anonymize_tag_recurse(ds: pydicom.Dataset, initial_str, new_str):
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


def main(CTP_data_folder, original_cohort, ids_file):
    ids_pairs = np.loadtxt(ids_file, dtype=str)

    # [Patch] just to be able to handle single folder cases inside the ids_file
    if not isinstance(ids_pairs[0], np.ndarray):
        ids_pairs = np.array([ids_pairs])

    for pair in ids_pairs:
        original_subject_folder = join(original_cohort, pair[0])
        ctp_subject_folder = join(CTP_data_folder, pair[1])

        # [Todo] needs an exception when it can't find the pair of tags
        dangerous_tag_pairs = get_dangerous_tag_pairs(original_subject_folder, ctp_subject_folder)
        print(dangerous_tag_pairs)

        for dirpath, dirnames, filenames in os.walk(ctp_subject_folder):
            for filename in filenames:
                ctp_file_path = join(dirpath, filename)
                ctp_file_image = pydicom.dcmread(ctp_file_path)
                ctp_dicom_corrected = ctp_file_image  # not necessary, just for clarity

                for dangerous_tag in dangerous_tag_pairs:
                    ctp_dicom_corrected = anonymize_tag_recurse(ctp_dicom_corrected, dangerous_tag[0], dangerous_tag[1])

                ctp_dicom_corrected.save_as(ctp_file_path)  # No turning back




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Dangerous tags process and recursive overwrite of DICOM images.")
    parser.add_argument('CTP_data_folder', type=str, help="Path to the CTP data folder.")
    parser.add_argument('original_cohort', type=str, help="Path to the original cohort folder.")
    parser.add_argument('ids_file', type=str, help="Path to the IDs file generated byt the CTP batcher file.")

    args = parser.parse_args()

    main(args.CTP_data_folder, args.original_cohort, args.ids_file)

