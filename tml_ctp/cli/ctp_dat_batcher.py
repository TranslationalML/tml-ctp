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
    new_patient_id: str = None,
    dateinc: int = None,
    image_tag: str = f"{__container_name__}:{__version__}",
):
    """Run DAT.jar with Docker given the input folder, output folder and DAT script.

    Args:
        input_folder (str): Path to the folder of files to be anonymized
        output_folder (str): Path to the folder where the anonymized files will be saved
        dat_script (str): Path to the DAT script to be used for anonymization
        new_patient_id (str): New PatientID to use in the DAT script
        dateinc (int): New DATEINC value to use in the DAT script
        image_tag (str): Tag of the Docker image to use for running DAT.jar (default: tml-ctp-anonymizer:<version>)

    Returns:
        tuple: Tuple containing the new PatientID, PatientName, and DATEINC values

    Raises:
        Exception: If the Docker run command fails with a non-zero return code
    """
    # Update the DAT script with new PatientID, PatientName and DATEINC values
    (new_patient_id, new_patient_name, dateinc) = update_dat_script_file(
        dat_script, new_patient_id=new_patient_id, dateinc=dateinc
    )
    # Create the command to run DAT.jar with Docker
    cmd = create_docker_dat_command(
        input_folder=input_folder,
        output_folder=output_folder,
        dat_script=dat_script,
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
    return (new_patient_id, new_patient_name, dateinc)


def update_dat_script_file(
    original_dat_script: str, new_patient_id: str = None, dateinc: int = None
):
    """Update the DAT script with a new DATEINC value, a new PatientID, and new random UUID for PatientName.

    If `new_patient_id` is `None`, a new random UUID for the PatientID is generated.
    If `dateinc` is `None`, a new random DATEINC value is generated between -30 and 30.

    Note that this function assumes that the DATEINC is always at the second line of the DAT script.
    Moreover, the original DAT script is modified in place and the new DATEINC value is returned.

    If the PatientID line or the PatientName line does not exist, they are appended to the end of the file.

    Args:
        original_dat_script (str): Path to the original DAT script
        new_patient_id (str): New PatientID to use in the DAT script
        dateinc (int): New DATEINC value to use in the DAT script

    Returns:
        tuple: Tuple containing the new PatientID, PatientName, and DATEINC values

    Raises:
        ValueError: If the DATEINC is not found in the second line of the DAT script
    """
    with open(original_dat_script, "r") as f:
        lines = f.readlines()

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
        lines.append(f'<e en="T" t="00100020" n="PatientID">{new_patient_id}</e>\n')

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
        lines.append(f'<e en="T" t="00100010" n="PatientName">{new_patient_name}</e>\n')

    with open(original_dat_script, "w") as f:
        f.writelines(lines)

    return (
        new_patient_id,
        new_patient_name,
        dateinc,
    )  # Return the generated values as a tuple


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
    CTP_ids_file = os.path.join(
        CTP_output_folder, f"CTP_{input_folders.split('/')[-2]}_newids_dateinc_log.csv"
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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
