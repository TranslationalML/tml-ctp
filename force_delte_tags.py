import os
import pydicom

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
print(replace_substr_in_tag('<tag>some sensitive info</tag>', 'sensitive', 'replaced', '<tag>', 'This is a <replaced> secret </replaced>'))


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

def process_dicom_file(filepath, tags_to_delete):
    """Modify the DICOM file to remove specified tags."""
    ds = pydicom.dcmread(filepath)
    modified = False

    for tag in tags_to_delete:
        if tag in ds:
            del ds[tag]  # Remove the specified tag
            modified = True

    if modified:
        ds.save_as(filepath)    # Overwrite the original file
        print(f"Modified {filepath}")

def process_directory(directory, tags_to_delete):
    """Recursively process all DICOM files in a directory."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".dcm"):  # Check for .dcm extension; This is the case of CTP data, but not for RAW CHUV
                process_dicom_file(os.path.join(root, file), tags_to_delete)

# # Specify the tags you want to delete
# tags_to_delete = [(0x0008, 0x1250),(0x0008,0x0031)]  

# # Specify the directory containing the DICOM files
# dicom_directory = "/media/TMLHD4/CTP/roots/DirectoryStorageService/"
# process_directory(dicom_directory, tags_to_delete)


sensible_tags = []

ctp_dicom = pydicom.dcmread('/media/SDD4T2/delivery_ASAP_Siemens/sub-2199415271/ses-20190524001934/6001_ep2d_diff_AVC/1.2.840.113654.2.70.1.20012587678525810311762139247823081.dcm')

original_dicom = pydicom.dcmread("/media/TMLHD4/ASTRAL/sub-1048724/ses-20190428001934/06001-ep2d_diff_AVC/MR.1.3.12.2.1107.5.2.50.175636.30000019042800220136200000485")

# Extract the sensible tags
patient_id = original_dicom.PatientID
series_date = original_dicom.SeriesDate

sensible_tags.append(patient_id)

ctp_dicom_corrected = anonymize_tag_recurse(ctp_dicom, patient_id, ctp_dicom.PatientID)

ctp_dicom_corrected = anonymize_tag_recurse(ctp_dicom_corrected, series_date, ctp_dicom.SeriesDate)

dangerous_tag_names = []

# Callback function to search for sensible tags
def search_for_sensible_tags(dataset, data_element):
    for tag in sensible_tags:
        if tag in str(data_element.value):
            print(f"*** Sensible tag found '{tag}' in element {data_element.name} with value {data_element.value}")
            dangerous_tag_names.append(data_element.name)


# Walk the ctp_dicom dataset using the callback function
ctp_dicom_corrected.walk(search_for_sensible_tags)