import os
import pydicom

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

# Specify the tags you want to delete
tags_to_delete = [(0x0008, 0x1250),(0x0008,0x0031)]  

# Specify the directory containing the DICOM files
dicom_directory = "/media/TMLHD4/CTP/roots/DirectoryStorageService/"
process_directory(dicom_directory, tags_to_delete)
