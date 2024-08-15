#!/bin/env python3

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

"""Script to run DAT.jar (CTP DicomAnonymizerTool) to anonymize DICOM files.

Usage:

    python3 ctp_dat_batcher.py \
        -i /path/to/input/folder \
        -o /path/to/output/folder \
        -s /path/to/dat/script
"""

try:
    import getpass
except ImportError:
    pass
import json
import os
import os.path
import platform
import sys
import time
import argparse
import shutil
import subprocess
import random
import uuid
import pydicom
import numpy as np
import tempfile
from pydicom.uid import generate_uid
from random import randint
from typing import List, Tuple
from pathlib import Path


from tml_ctp.info import __version__, __container_name__


def is_windows_platform():
    return platform.system() == "Windows"


def run(cmd: list):
    """Run the given command using subprocess.run.

    Args:
        cmd (list): Command to run to be passed to subprocess.Popen
    """
    process = subprocess.run(cmd)
    return process


def create_docker_dat_command(
    input_folder: str,
    output_folder: str,
    dat_script: str,
    image_tag: str = f"{__container_name__}:{__version__}",
):
    """Create the command to run DAT.jar with Docker.

    This generates a command to run DAT.jar with Docker in the following format:

        docker run --rm \
            -u <user_id>:<group_id> \
            -v <input_folder>:/input \
            -v <output_folder>:/output \
            -v <dat_script>:/scripts/da.script \
            <image_tag> \
            -in /input \
            -out /output \
            -da /scripts/da.script

    Args:
        input_folder (str): Path to the folder of files to be anonymized
        output_folder (str): Path to the folder where the anonymized files will be saved
        dat_script (str): Path to the DAT script to be used for anonymization
        image_tag (str): Tag of the Docker image to use for running DAT.jar (default: ctp-anonymizer:<version>)

    Returns:
        list: The command to run DAT.jar with Docker

    """

    if is_windows_platform():
        user_id = getpass.getuser()
        group_id = 0
    else:  # Linux or Mac
        user_id = os.geteuid()
        group_id = os.getegid()

    cmd = [
        "docker",
        "run",
        "--rm",
        "-u",
        f"{user_id}:{group_id}",
        "-v",
        f"{input_folder}:/input",
        "-v",
        f"{output_folder}:/output",
        "-v",
        f"{dat_script}:/scripts/anonymizer.script",
        image_tag,
        "-in",
        "/input",
        "-out",
        "/output",
        "-da",
        "/scripts/anonymizer.script",
    ]
    return cmd


def run_dat(
    input_folder: str,
    output_folder: str,
    dat_script: str,
    temp_dir: str,
    new_patient_id: str = None,
    dateinc: int = None,
    image_tag: str = f"{__container_name__}:{__version__}",
):
    """Run DAT.jar with Docker given the input folder, output folder and DAT script.

    Args:
        input_folder (str): Path to the folder of files to be anonymized.
        output_folder (str): Path to the folder where the anonymized files will be saved.
        dat_script (str): Path to the DAT script to be used for anonymization.
        temp_dir (str): Path to the temporary directory.
        new_patient_id (str): New PatientID to use in the DAT script.
        dateinc (int): New DATEINC value to use in the DAT script.
        image_tag (str): Tag of the Docker image to use for running DAT.jar (default: tml-ctp-anonymizer:<version>).

    Returns:
        tuple: Tuple containing the new PatientID, PatientName, DATEINC values, and the path to the modified DAT script.

    Raises:
        Exception: If the Docker run command fails with a non-zero return code.
    """
    # Update the DAT script with new PatientID, PatientName and DATEINC values
    (new_patient_id, new_patient_name, new_series_uid, dateinc, updated_dat_script) = update_dat_script_file(
        dat_script, temp_dir, new_patient_id=new_patient_id, dateinc=dateinc
    )
    # Get the set of all patient names saved in dicoms
    patient_identifiers_set = get_patient_identifiers(input_folder)
    # Create the command to run DAT.jar with Docker
    cmd = create_docker_dat_command(
        input_folder=input_folder,
        output_folder=output_folder,
        dat_script=updated_dat_script,
        image_tag=image_tag,
    )
    # Run the command
    print(f"Running DAT with command: {' '.join(cmd)}")
    print("with updated script containing:")
    print(f"\t- PatientID: {new_patient_id}")
    print(f"\t- PatientName: {new_patient_name}")
    print(f"\t- DATEINC: {dateinc}")
    process = run(cmd)
    if process.returncode != 0:
        raise Exception(
            f"Command {cmd} failed (return code {process.returncode}) "
            f"with the following error:\n {process.stderr}"
        )
    # Check if patient name present in output folder
    check_and_rename_dicom_files(output_folder, patient_identifiers_set, str(new_series_uid))
    return (new_patient_id, new_patient_name, dateinc)


def update_dat_script_file(
    original_dat_script: str, temp_dir: str, new_patient_id: str = None, dateinc: int = None
) -> Tuple[str, str, int, str]:
    """Update the DAT script with a new DATEINC value, a new PatientID, and new random UUID for PatientName.
    Additionally, update or add SeriesInstanceUID.

    If `new_patient_id` is `None`, a new random UUID for the PatientID is generated.
    If `dateinc` is `None`, a new random DATEINC value is generated between -30 and 30.

    This function assumes that the DATEINC is always at the second line of the DAT script.
    The original DAT script is copied to a new script with a random number appended to the name,
    and the modifications are applied to this new script.

    If the PatientID line or the PatientName line does not exist, they are appended to the end of the file.
    If the SeriesInstanceUID line does not exist, it is inserted before the closing </script> tag.

    Args:
        original_dat_script (str): Path to the original DAT script.
        temp_dir (str): Path to a temporary directory where to store the copy of the DAT script.
        new_patient_id (str): New PatientID to use in the DAT script.
        dateinc (int): New DATEINC value to use in the DAT script.

    Returns:
        tuple: Tuple containing the new PatientID, PatientName, SeriesInstanceUID, DATEINC values, and the path to the modified DAT script.

    Raises:
        ValueError: If the DATEINC is not found in the second line of the DAT script.
    """
    # Generate a random number for the new script name
    random_suffix = random_with_N_digits(8)
    new_dat_script = os.path.join(temp_dir, f"anonymizer_{random_suffix}.script")

    # Copy the original script to the new script with the random suffix
    shutil.copyfile(original_dat_script, new_dat_script)

    # Read the lines from the new script file
    with open(new_dat_script, "r") as f:
        lines = f.readlines()
    # Find the index of end script tag
    end_script_index = next((i for i, line in enumerate(lines) if '</script>' in line), None)

    # Find the index of the end script tag
    end_script_index = next((i for i, line in enumerate(lines) if '</script>' in line), None)

    # Assuming the DATEINC is always at the second line
    if "DATEINC" not in lines[1]:
        raise ValueError("DATEINC not found in the second line of the DAT script")
    if dateinc is None:
        dateinc = random.randint(-30, 30)
    lines[1] = f' <p t="DATEINC">{dateinc}</p>\n'

    # Generate a UUID for the PatientID
    if new_patient_id is None:
        new_patient_id = str(uuid.uuid4().int)[:11]

    # Find the line that sets the PatientID and modify it
    patient_id_line_index = next(
        (i for i, line in enumerate(lines) if 'n="PatientID"' in line), None
    )
    if patient_id_line_index is not None:
        lines[patient_id_line_index] = (
            f'<e en="T" t="00100020" n="PatientID">{new_patient_id}</e>\n'
        )
    else:
        # If the PatientID line does not exist, append it to the end
        lines.insert(end_script_index, f'<e en="T" t="00100020" n="PatientID">{new_patient_id}</e>\n')

    # Generate a UUID for the PatientName
    new_patient_name = str(uuid.uuid4().int)[:7]

    # Find the line that sets the PatientName and modify it
    patient_name_line_index = next(
        (i for i, line in enumerate(lines) if 'n="PatientName"' in line), None
    )
    if patient_name_line_index is not None:
        lines[patient_name_line_index] = (
            f'<e en="T" t="00100010" n="PatientName">{new_patient_name}</e>\n'
        )
    else:
        # If the PatientName line does not exist, append it to the end
        lines.insert(end_script_index, f'<e en="T" t="00100010" n="PatientName">{new_patient_name}</e>\n')

    # Find the line with UIDROOT and extract its value
    uidroot_line = next((line for line in lines if 't="UIDROOT"' in line), None)
    if uidroot_line:
        uidroot_value = uidroot_line.split('>')[1].split('<')[0]  # Extract the value between the tags
        # Ensure the prefix ends with a period
        if not uidroot_value.endswith('.'):
            uidroot_value += '.'
    else:
        # If UIDROOT line does not exist, insert it before the closing </script> tag
        default_uidroot = '1.2.826.0.1.3680043.8.498'
        lines.insert(end_script_index, f'<p t="UIDROOT">{default_uidroot}</p>\n')
        
        # Use the default value with a period for the prefix
        uidroot_value = f'{default_uidroot}.'

    # Generate a new SeriesInstanceUID
    new_series_uid = generate_uid(prefix=uidroot_value)
    # Find the line that sets the SeriesInstanceUID and modify it
    series_uid_line_index = next(
        (i for i, line in enumerate(lines) if 'n="SeriesInstanceUID"' in line), None
    )
    if series_uid_line_index is not None:
        lines[series_uid_line_index] = (
            f'<e en="T" t="0020000E" n="SeriesInstanceUID">{new_series_uid}</e>\n'
        )
    else:
        # If the SeriesInstanceUID line does not exist, insert it before the closing </script> tag
        lines.insert(end_script_index, f'<e en="T" t="0020000E" n="SeriesInstanceUID">{new_series_uid}</e>\n')

    with open(new_dat_script, "w") as f:
        f.writelines(lines)

    return (
        new_patient_id,
        new_patient_name,
        new_series_uid,
        dateinc,
        new_dat_script,
    )  # Return the generated values and the path to the new script as a tuple


def rename_ctp_output_subject_folders(CTP_output_folder: str, subject_folder: str):
    """Rename the subject / session folders in the CTP output to match the new IDs generated by DAT.

    1. Get the new PatientID, StudyDate and StudyTime from the anonymized DICOM files with pydicom
    2. Rename the subject folder to match the new PatientID
    3. Rename the session folder to match the new StudyDate and StudyTime
    4. Write the mapping between the old and new IDs to a file

    Args:
        CTP_output_folder (str): Path to the folder where the anonymized files are saved
        subject_folder (str): Name of the subject folder to be renamed

    Raises:
        Exception: If an error occurs while reading or copying the DICOM files
    """
    print(f"Renaming {subject_folder}")
    print(f"CTP output folder: {CTP_output_folder}")
    for session_dir in os.listdir(os.path.join(CTP_output_folder, subject_folder)):
        session_dir_path = os.path.join(
            os.path.join(CTP_output_folder, subject_folder), session_dir
        )

        for series_dir in os.listdir(session_dir_path):
            series_dir_path = os.path.join(session_dir_path, series_dir)

            for file in os.listdir(series_dir_path):
                file_path = os.path.join(series_dir_path, file)

                try:
                    ds = pydicom.dcmread(file_path)
                    new_patient_id = ds.PatientID
                    # Check if StudyDate and StudyTime attributes are present in the DICOM dataset object
                    new_study_date = (
                        ds.StudyDate if hasattr(ds, "StudyDate") else "NoStudyDate"
                    )
                    new_study_time = (
                        ds.StudyTime if hasattr(ds, "StudyTime") else "NoStudyTime"
                    )
                    new_series_number = (
                        ds.SeriesNumber
                        if hasattr(ds, "SeriesNumber")
                        else "NoSeriesNumber"
                    )
                    new_series_desc = (
                        ds.SeriesDescription
                        if hasattr(ds, "SeriesDescription")
                        else "NoSeriesDescription"
                    )
                except Exception as e:
                    raise Exception(f"An error occurred while reading {file_path}: {e}")

                print(f"New PatientID: {new_patient_id}")
                print(f"New StudyDate: {new_study_date}")
                print(f"New StudyTime: {new_study_time}")
                print(f"New SeriesNumber: {new_series_number}")
                print(f"New SeriesDescription: {new_series_desc}")

                new_series_dir_path = os.path.join(
                    CTP_output_folder,
                    f"sub-{new_patient_id}",
                    f"ses-{new_study_date}{new_study_time}",
                    f"{new_series_number}_{new_series_desc}",
                )

                try:
                    print(f"Renaming {series_dir_path} to {new_series_dir_path}")
                    shutil.copytree(
                        series_dir_path,
                        new_series_dir_path,
                        symlinks=False,
                        ignore=None,
                        ignore_dangling_symlinks=False,
                        dirs_exist_ok=True,
                    )
                    shutil.rmtree(series_dir_path, ignore_errors=True)
                except Exception as e:
                    raise Exception(
                        f"An error occurred while copying {series_dir_path} to {new_series_dir_path}: {e}"
                    )

                break
    shutil.rmtree(os.path.join(CTP_output_folder, subject_folder), ignore_errors=True)


def get_parser():
    """Get the parser for the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run DAT.jar (CTP DicomAnonymizerTool) with Docker to anonymize DICOM files."
    )
    parser.add_argument(
        "-i",
        "--input-folders",
        type=str,
        required=True,
        help="Parent folder including all folders of files to be anonymized.",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=str,
        required=True,
        help="Folder where the anonymized files will be saved.",
    )
    parser.add_argument(
        "-s",
        "--dat-script",
        type=str,
        required=True,
        help="Script to be used for anonymization by the DAT.jar tool.",
    )
    parser.add_argument(
        "--new-ids",
        type=str,
        required=False,
        default=None,
        help="JSON file generated by pacsman-get-pseudonyms containing the mapping between the old and new patient IDs. "
        "It should in the format {'old_id1': 'new_id1', 'old_id2': 'new_id2', ...}. "
        "If not provided, the script will generate a new ID randomly.",
    )
    parser.add_argument(
        "--day-shift",
        type=str,
        required=False,
        default=None,
        help="JSON file containing the day shift / increment to use for each patient ID. "
        "The old patient ID is the key and the day shift is the value, e.g. {'old_id1': 5, 'old_id2': -3, ...}. "
        "If not provided, the script will generate a new day shift randomly.",
    )
    parser.add_argument(
        "--image-tag",
        type=str,
        required=False,
        default=f"quay.io/translationalml/{__container_name__}:{__version__}",
        help="Tag of the Docker image to use for running DAT.jar (default: tml-ctp-anonymizer:<version>).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__}",
    )
    return parser


def check_and_rename_dicom_files(dicom_folder: str, patient_identifiers: set[str], replacement_string: str) -> None:
    """Check if any DICOM filename contains any of the patient names and, if found, rename the files with anonymized filenames.

    This function scans through the specified folder containing DICOM files to detect any filenames that include the patient names.
    If such filenames are found, it renames these files by replacing the patient names with a new anonymized name.

    Args:
        dicom_folder (str): Path to the folder containing DICOM files.
        patient_identifiers (set[str]): A set of strings representing patient identifiers to check for in the DICOM filenames.
        replacement_string (str): The string to replace the patient name with.
    """
    any_needs_renaming = False

    # Gather all DICOM file paths
    file_paths = []
    for root, _, files in os.walk(dicom_folder):
        for file in files:
            if file.endswith(".dcm"):
                file_paths.append(Path(root) / file)

    # First pass to check if any file contains the patient names
    for file_path in file_paths:
        try:
            for patient_identifier in patient_identifiers:
                if patient_identifier.lower() in file_path.name.lower():
                    any_needs_renaming = True
                    break
            if any_needs_renaming:
                break
        except Exception as e:
            print(f"An error occurred while processing {file_path}: {e}")

    # If any file contains a patient name, proceed with renaming
    if any_needs_renaming:
        # Sort the file paths to have the right slice order
        sorted_file_paths = get_sorted_image_files(file_paths)

        for index, file_path in enumerate(sorted_file_paths, start=0):
            try:
                # Prepare new filename
                new_filename = file_path.name
                for patient_identifier in patient_identifiers:
                    new_filename = new_filename.lower().replace(patient_identifier.lower(), replacement_string)

                # Rename file
                new_file_path = file_path.with_name(new_filename)
                file_path.rename(new_file_path)
                print(f"File renamed to: {new_file_path}")

            except Exception as e:
                print(f"An error occurred while processing {file_path}: {e}")


def get_sorted_image_files(file_paths: List[str]) -> Tuple[List[str], str]:
    """Sort DICOM image files in increasing slice order.

    Args:
        file_paths (list): List of file paths to DICOM files.

    Returns:
        list: Sorted file paths.
    """
    if len(file_paths) == 0:
        return file_paths

    # Use the first file to get reference orientation and position
    ref_file = file_paths[0]
    ds = pydicom.dcmread(ref_file)
    ref_position = np.array([float(x) for x in ds.ImagePositionPatient])
    ref_orientation = np.array([float(x) for x in ds.ImageOrientationPatient])

    # Determine out-of-plane direction for the first slice
    x = ref_orientation[:3]
    y = ref_orientation[3:]
    scan_axis = np.cross(x, y)
    scan_origin = ref_position

    # Calculate distance along the scan axis for each file
    sort_list = []
    for file in file_paths:
        ds = pydicom.dcmread(file)
        position = np.array([float(x) for x in ds.ImagePositionPatient])
        vec = position - scan_origin
        dist = np.dot(vec, scan_axis)
        sort_list.append((file, dist))

    # Sort files by distance
    sorted_files = sorted(sort_list, key=lambda x: x[1])

    # Extract sorted file paths
    sorted_file_paths = [file for file, _ in sorted_files]

    return sorted_file_paths


def get_patient_identifiers(dicom_folder: str) -> set[str]:
    """
    Get a set of unique patient identifiers from the DICOM files in the specified folder.

    Args:
        dicom_folder (str): Path to the folder containing DICOM files.

    Returns:
        set[str]: A set containing unique patient idenfiers found in the DICOM files.
    """
    patient_identifiers = set()

    for root, _, files in os.walk(dicom_folder):
        for file in files:
            if file.endswith(".dcm"):
                file_path = Path(root) / file
                try:
                    ds = pydicom.dcmread(file_path)
                    patient_name = str(ds.PatientName).strip()
                    patient_identifiers.add(patient_name)
                except Exception as e:
                    print(f"An error occurred while processing {file_path}: {e}")

    return patient_identifiers


def random_with_N_digits(n: int) -> int:
    """
    Generates a random integer with the specified number of digits.

    Args:
        n (int): The number of digits for the random integer. Must be greater than 0.

    Returns:
        int: A random integer with exactly n digits.

    Raises:
        ValueError: If n is less than or equal to 0.
    """
    if n <= 0:
        raise ValueError("Number of digits must be greater than 0")

    random_instance = random.Random()

    # Generate the first digit from 1 to 9 to ensure it is not zero
    first_digit = random_instance.choice('123456789')

    # Generate the remaining digits from 0 to 9
    remaining_digits = ''.join(random_instance.choices('0123456789', k=n - 1))

    # Combine the digits into a single number
    number = int(first_digit + remaining_digits)

    return number


def main():
    """Main function of the `ctp_dat_batcher` script which anonymize DICOM files.

    This script takes as input a folder containing folders of DICOM files to be anonymized.
    It then runs DAT.jar (CTP DicomAnonymizerTool) with Docker to anonymize the DICOM files.
    The anonymized files are saved in a folder specified by the user.

    The script also renames the subject / session folders in the CTP output to match the new IDs generated by DAT.

    The script also writes the mapping between the old and new IDs to a file.

    """
    start_time = time.time()

    parser = get_parser()
    args = parser.parse_args()
    input_folders = args.input_folders
    CTP_output_folder = args.output_folder
    dat_script = args.dat_script
    image_tag = args.image_tag

    # Create the temporary directory
    temp_dir = tempfile.mkdtemp(prefix="ctp_anonymizer_scripts_")

    try:
        # Check if the input folder exists
        if not os.path.exists(input_folders):
            print(
                f"ERROR: The input folder {input_folders} does not exist. Please check the path!"
            )
            sys.exit(1)

        # Check if the DAT script exists
        if not os.path.exists(dat_script):
            print(
                f"ERROR: The DAT script {dat_script} does not exist. Please check the path!"
            )
            sys.exit(1)

        # Check if the new IDs file exists
        if args.new_ids is not None and not os.path.exists(args.new_ids):
            print(
                f"ERROR: The new IDs file {args.new_ids} does not exist. Please check the path!"
            )
            sys.exit(1)

        # Check if the day shifts file exists
        if args.day_shift is not None and not os.path.exists(args.day_shift):
            print(
                f"ERROR: The day shifts file {args.day_shift} does not exist. Please check the path!"
            )
            sys.exit(1)

        # Create the output folder if it does not exist
        os.makedirs(CTP_output_folder, exist_ok=True)

        # Load the new patient IDs from the JSON file
        if args.new_ids is not None:
            with open(args.new_ids, "r") as file:
                try:
                    new_patient_ids = json.load(file)
                except json.JSONDecodeError as e:
                    print(f"An error occurred while loading the new IDs file: {e}")
                    sys.exit(1)
        else:
            new_patient_ids = None

        # Load the day shifts from the JSON file
        if args.day_shift is not None:
            with open(args.day_shift, "r") as file:
                try:
                    day_shifts = json.load(file)
                except json.JSONDecodeError as e:
                    print(f"An error occurred while loading the day shifts file: {e}")
                    sys.exit(1)
                # Check that the day shifts are integers
                for k, v in day_shifts.items():
                    if not isinstance(v, int):
                        print(
                            f"ERROR: The day shift for patient {k} is not an integer. Please check the file!"
                        )
                        sys.exit(1)
        else:
            day_shifts = None

        # Get the list of all patient folders
        all_patient_folders = [
            dir
            for dir in os.listdir(input_folders)
            if os.path.isdir(os.path.join(input_folders, dir))
        ]
        all_patient_folders.sort()

        # Create a file to store the mapping between the old and new IDs and the DATEINC values

        input_path = Path(input_folders).resolve()
        parent_dir_name = input_path.parent.name if input_path.parent != input_path else input_path.name
        CTP_ids_file = os.path.join(
            CTP_output_folder, f"CTP_{parent_dir_name}_newids_dateinc_log.csv"
        )
        with open(CTP_ids_file, "a") as file:
            for i, folder in enumerate(all_patient_folders):
                print(f"Processing {folder} [{i+1}/{len(all_patient_folders)}]")

                if new_patient_ids is not None:
                    new_patient_id = new_patient_ids[folder]
                else:
                    new_patient_id = None

                if day_shifts is not None:
                    dateinc = day_shifts[folder]
                else:
                    dateinc = None

                try:
                    os.makedirs(os.path.join(CTP_output_folder, folder), exist_ok=True)
                    (new_patient_id, _, dateinc) = run_dat(
                        input_folder=os.path.join(input_folders, folder),
                        output_folder=os.path.join(CTP_output_folder, folder),
                        dat_script=dat_script,
                        temp_dir=temp_dir,  # Pass the temporary directory
                        new_patient_id=new_patient_id,
                        dateinc=dateinc,
                        image_tag=image_tag,
                    )
                except Exception as e:
                    # TODO: see how to handle this error (e.g. break, continue, etc.)
                    print(f"An error occurred while processing {folder}: {e}")

                # Rename the subject / session folders in the CTP output to match the new IDs generated by DAT
                rename_ctp_output_subject_folders(CTP_output_folder, folder)

                # Write the mapping between the old and new IDs and the DATEINC values to the file
                info = f"{folder}, sub-{new_patient_id}, {dateinc}\n"
                file.write(info)
                file.flush()
                print(info)

                end_time = time.time()
                elapsed_time = end_time - start_time
                expected_time_per_iteration = elapsed_time / (i + 1)
                expected_total_time = expected_time_per_iteration * len(all_patient_folders)
                print(f"Expected total time: {expected_total_time} seconds")

    finally:
        # Cleanup the temporary directory
        shutil.rmtree(temp_dir)
        print(f"Temporary directory {temp_dir} removed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")