#!/bin/env python3

# Copyright (C) 2023, The TranslationalML team and Contributors. All rights reserved.
#  This software is distributed under the open-source Apache 2.0 license.

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
import os
import os.path
import platform
import time
import argparse
import shutil
import subprocess
import random
import uuid
import pydicom


def get_new_folder_id(CTP_output_folder: str, previous_folders: list):
    """Get a new folder ID for a given folder.

    Args:
        CTP_output_folder (str): Path to the folder where the anonymized files are saved
        previous_folders (list): List of folders that have already been processed
    """
    folder = [
        dir
        for dir in os.listdir(CTP_output_folder)
        if os.path.isdir(os.path.join(CTP_output_folder, dir))
        and dir not in previous_folders
    ]
    return folder[0]


def is_windows_platform():
    return platform.system() == "Windows"


def run(cmd: list):
    """Run the given command using subprocess.run.

    Args:
        cmd (list): Command to run to be passed to subprocess.Popen
    """
    process = subprocess.run(cmd)
    return process


def create_docker_dat_command(input_folder: str, output_folder: str, dat_script: str):
    """Create the command to run DAT.jar with Docker.
    
    This generates a command to run DAT.jar with Docker in the following format:
    
        docker run --rm \
            -v <input_folder>:/input \
            -v <output_folder>:/output \
            -v <dat_script>:/scripts/da.script \
            ctpdat:0.0.1 \
            -in /input \
            -out /output \
            -da /scripts/da.script

    Args:
        input_folder (str): Path to the folder of files to be anonymized
        output_folder (str): Path to the folder where the anonymized files will be saved
        dat_script (str): Path to the DAT script to be used for anonymization
    
    Returns:
        list: The command to run DAT.jar with Docker

    """

    if is_windows_platform():
        user_id = getpass.getuser()
        group_id = 0
    else:  # Linux or Mac
        user_id = os.geteuid()
        group_id = os.getegid()

    image_tag = "astral-ctp-anonymizer:0.0.1"
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


def run_dat(input_folder: str, output_folder: str, dat_script: str):
    """Run DAT.jar with Docker given the input folder, output folder and DAT script.

    Args:
        input_folder (str): Path to the folder of files to be anonymized
        output_folder (str): Path to the folder where the anonymized files will be saved
        dat_script (str): Path to the DAT script to be used for anonymization
    """
    # Update the DAT script with a new random DATEINC
    update_dat_script_file(dat_script)
    # Create the command to run DAT.jar with Docker
    cmd = create_docker_dat_command(input_folder, output_folder, dat_script)
    # Run the command
    print(f"Running DAT with command: {' '.join(cmd)}")
    process = run(cmd)
    if process.returncode != 0:
        raise Exception(
            f"Command {cmd} failed (return code {process.returncode}) "
            f"with the following error:\n {process.stderr}"
        )


def update_dat_script_file(original_dat_script: str):
    """Update the DAT script with a new random DATEINC.

    Note that this function assumes that the DATEINC is always at the second line of the DAT script.
    Moreover, the original DAT script is modified in place and the new DATEINC value is returned.

    Args:
        original_dat_script (str): Path to the original DAT script
    """
    with open(original_dat_script, "r") as f:
        lines = f.readlines()

    # Assuming the DATEINC is always at the second line
    dateinc_value = random.randint(-30, 30)
    lines[1] = f' <p t="DATEINC">{dateinc_value}</p>\n'

    # Generate a UUID for the PatientID
    patient_id_uuid = str(uuid.uuid4().int)[:11]

    # Find the line that sets the PatientID and modify it
    patient_id_line_index = next(
        (i for i, line in enumerate(lines) if 'n="PatientID"' in line), None
    )
    if patient_id_line_index is not None:
        lines[
            patient_id_line_index
        ] = f'<e en="T" t="00100020" n="PatientID">{patient_id_uuid}</e>\n'
    else:
        # If the PatientID line does not exist, append it to the end
        lines.append(f'<e en="T" t="00100020" n="PatientID">{patient_id_uuid}</e>\n')

    # Generate a UUID for the PatientName
    patient_name_uuid = str(uuid.uuid4().int)[:7]

    # Find the line that sets the PatientName and modify it
    patient_name_line_index = next(
        (i for i, line in enumerate(lines) if 'n="PatientName"' in line), None
    )
    if patient_name_line_index is not None:
        lines[
            patient_name_line_index
        ] = f'<e en="T" t="00100010" n="PatientName">{patient_name_uuid}</e>\n'
    else:
        # If the PatientName line does not exist, append it to the end
        lines.append(
            f'<e en="T" t="00100010" n="PatientName">{patient_name_uuid}</e>\n'
        )

    with open(original_dat_script, "w") as f:
        f.writelines(lines)

    return dateinc_value  # Return the generated value


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
                    new_study_date = ds.StudyDate
                    new_study_time = ds.StudyTime
                    new_series_number = ds.SeriesNumber
                    new_series_desc = ds.SeriesDescription
                except Exception as e:
                    raise Exception(f"An error occurred while reading {file_path}: {e}")

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

    all_patient_folders = [
        dir
        for dir in os.listdir(input_folders)
        if os.path.isdir(os.path.join(input_folders, dir))
    ]
    all_patient_folders.sort()

    CTP_folder_list = [
        dir
        for dir in os.listdir(CTP_output_folder)
        if os.path.isdir(os.path.join(CTP_output_folder, dir))
    ]

    ASTRAL_CTP_ids_file = f"ASTRAL_CTP_{input_folders.split('/')[-2]}_ids.txt"

    with open(ASTRAL_CTP_ids_file, "a") as file:
        for i, folder in enumerate(all_patient_folders):
            print(f"Processing {folder} [{i+1}/{len(all_patient_folders)}]")

            try:
                os.makedirs(os.path.join(CTP_output_folder, folder), exist_ok=True)
                run_dat(
                    input_folder=os.path.join(input_folders, folder),
                    output_folder=os.path.join(CTP_output_folder, folder),
                    dat_script=dat_script,
                )
            except Exception as e:
                # TODO: see how to handle this error (e.g. break, continue, etc.)
                print(f"An error occurred while processing {folder}: {e}")

            # Rename the subject / session folders in the CTP output to match the new IDs generated by DAT
            rename_ctp_output_subject_folders(CTP_output_folder, folder)

            try:
                new_folder = get_new_folder_id(CTP_output_folder, CTP_folder_list)
                CTP_folder_list.append(new_folder)

                file.write(f"{folder} {new_folder}\n")
                file.flush()
                print(f"{folder} {new_folder}\n")
            except Exception as e:
                print(f"An error occurred while processing {folder}: {e}")
                break  # Stop processing further folders should be rested manually

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
