import os
import shutil
import glob
import pydicom


def create_custom_folder_structure(source_dir, dest_dir, depth):
    """
    Create a custom folder structure with the specified depth.

    Args:
        source_dir (str): The path to the original directory containing DICOM files.
        dest_dir (str): The path where the new structure will be created.
        depth (int): The number of subdirectories to create before placing DICOM files.
    """
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir)

    # Copy each DICOM file from source_dir into the new structure at the specified depth
    dicom_files = glob.glob(os.path.join(source_dir, "*", "*", "*", "*.dcm"))
    
    for idx, dicom_file in enumerate(dicom_files):
        # Generate subdirectories based on the depth argument
        subfolder_path = os.path.join(dest_dir, *[f"subdir_{i}" for i in range(depth)])

        # Create the directory if it doesn't exist
        os.makedirs(subfolder_path, exist_ok=True)

        # Copy the DICOM file to the new location
        shutil.copy2(dicom_file, os.path.join(subfolder_path, f"dicom_file_{idx}.dcm"))


def test_delete_identifiable_dicoms_script_basic(script_runner, test_dir, data_dir):

    test_dataset = "PACSMANCohort-delete_identifiable_dicoms"
    # Copy the dataset to a temporary folder with default structure
    default_dataset_path = os.path.join(test_dir, "tmp", test_dataset)
    shutil.copytree(
        os.path.join(data_dir, "PACSMANCohort"),
        default_dataset_path,
    )

    # Add missing SequenceName to all dicom files in the default test_dataset
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_dataset, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        ds.SequenceName = "tfl3d"
        ds.save_as(dicom_file)

    # Run the script with default folder depth (3)
    cmd = [
        "tml_ctp_delete_identifiable_dicoms",
        "--in_folder",
        default_dataset_path,
        "-t1w",
    ]

    ret = script_runner.run(cmd)

    # Check that the script has run successfully
    assert ret.success
    assert "Deleted 128 files" in ret.stdout

    # Check that all dicom files have been deleted as SequenceName is tfl3d 
    dicom_files = glob.glob(
        os.path.join(default_dataset_path, "*", "*", "*", "*.dcm")
    )
    assert len(dicom_files) == 0


def test_delete_identifiable_dicoms_with_custom_depth(script_runner, test_dir, data_dir):
    """
    Test the script with a custom folder depth (different from the default).
    """

    test_dataset = "PACSMANCohort-delete_identifiable_dicoms_custom"
    custom_depth = 5
    custom_dataset_path = os.path.join(test_dir, "tmp", f"{test_dataset}_depth_{custom_depth}")
    original_dataset_path = os.path.join(test_dir, "tmp", f"{test_dataset}_original")

    # Copy the original dataset
    shutil.copytree(
        os.path.join(data_dir, "PACSMANCohort"),
        original_dataset_path,
    )

    # Add missing SequenceName to all dicom files in the default test_dataset
    dicom_files = glob.glob(
        os.path.join(original_dataset_path, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        ds.SequenceName = "tfl3d"
        ds.save_as(dicom_file)

    # Create custom folder structure with depth 5
    create_custom_folder_structure(original_dataset_path, custom_dataset_path, custom_depth)

    # Run the script with the custom folder depth
    cmd = [
        "tml_ctp_delete_identifiable_dicoms",
        "--in_folder",
        custom_dataset_path,
        "-t1w",
        "--folder_depth",
        str(custom_depth),  # Provide custom folder depth
    ]

    ret = script_runner.run(cmd)

    # Check that the script has run successfully for custom depth
    assert ret.success
    assert "Deleted 128 files" in ret.stdout

    # Check that all dicom files have been deleted as SequenceName is tfl3d in the custom structure
    dicom_files = glob.glob(
        os.path.join(custom_dataset_path, *[f"subdir_{i}" for i in range(custom_depth)], "*.dcm")
    )
    assert len(dicom_files) == 0
