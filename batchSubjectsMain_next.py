from ast import AST
import sys, os
import os.path
import time
import subprocess
import random
import traceback
import string

# Function to check if any files are left in a given folder
def is_there_files_left(path):
    for r, d, f in os.walk(path):
        for file in f:
            return True
    return False

# Function to get a new folder ID for a given folder
def get_new_folder_id(CTP_output_folder, previous_folders):
    folder = [dir for dir in os.listdir(CTP_output_folder) if os.path.isdir(os.path.join(CTP_output_folder, dir)) and dir not in previous_folders]
    return folder[0]

def launch_ctp_runner(ctp_runner, first_time=True):
    if not first_time:
        # Terminate the existing CTP process if it is already running
        subprocess.run(['pkill', '-f', 'java'])
        time.sleep(5)  # Allow some time for the process to terminate

    # Launch the CTP Runner
    subprocess.Popen(['java', '-jar', ctp_runner],stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def update_config_file(original_config):
    with open(original_config, 'r') as f:
        lines = f.readlines()

    # Assuming the DATEINC is always at the second line
    dateinc_value = random.randint(-30, 30)
    lines[1] = f' <p t="DATEINC">{dateinc_value}</p>\n'

    with open(original_config, 'w') as f:
        f.writelines(lines)

    return dateinc_value  # Return the generated value

import os

def check_free_space(folder_path, required_space_gb=1):
    """Check if there's at least `required_space_gb` GB free space in the folder."""
    # Get disk usage statistics
    stat = os.statvfs(folder_path)
    # Calculate free space in GB
    free_space_gb = stat.f_bavail * stat.f_frsize / 1e9

    return free_space_gb >= required_space_gb



def main():
    start_time = time.time()
    first_time = True  # To track if CTP has been launched already


    CTP_directory = '/home/jonathan/Apps/CTP/'
    input_folders = '/media/jonathan/WDelements/ASTRAL/'
    original_config   = CTP_directory + 'scripts/DicomAnonymizer_Whitelist_extended.script'
    CTP_import_folder = CTP_directory + 'roots/DirectoryImportService/import/'
    CTP_queue_folder  = CTP_directory + 'roots/DirectoryImportService/queue/'
    CTP_output_folder = CTP_directory + 'roots/DirectoryStorageService/'

    ctp_runner = CTP_directory + 'Runner.jar'


    # Switch to the necessary directory
    os.chdir(CTP_directory)

    all_patient_folders = [dir for dir in os.listdir(input_folders) if os.path.isdir(os.path.join(input_folders, dir))]
    all_patient_folders.sort()
    print('Restricting patient list to first 450 patients to save time')
    all_patient_folders=all_patient_folders[0:450]

    CTP_folder_list = [dir for dir in os.listdir(CTP_output_folder) if os.path.isdir(os.path.join(CTP_output_folder, dir))]

    ASTRAL_CTP_ids_file = f"ASTRAL_CTP_{input_folders.split('/')[-2]}_ids.txt"

    # Launch the CTP Runner for the first time
    launch_ctp_runner(ctp_runner, first_time)
    first_time = False  # Mark that CTP has been launched


    last_processed_folder = None
    try:
        with open(ASTRAL_CTP_ids_file, 'r') as f:
            lines = f.readlines()
            if lines:
                last_processed_folder = lines[-1].split()[0]
                print(f'Resuming at {last_processed_folder}')

    except FileNotFoundError:
        pass

    with open(ASTRAL_CTP_ids_file, 'a') as file:
        for i, folder in enumerate(all_patient_folders):
            if last_processed_folder and folder <= last_processed_folder:
                continue

            # Update the configuration file with a new random DATEINC
            dateinc_value = update_config_file(original_config)

            # Relaunch the CTP Runner to use the new configuration
            launch_ctp_runner(ctp_runner, first_time)

            # Generate a random character
            random_char = random.choice(string.ascii_letters)

            # Copy the folder with a random character appended to its name
            new_folder_name = f"{folder}{random_char}"
            os.system(f"cp -r {os.path.join(input_folders, folder)} {os.path.join(CTP_import_folder, new_folder_name)}")

            print(f'Processing {folder} [{i+1}/{len(all_patient_folders)}]')

            while is_there_files_left(CTP_import_folder) or is_there_files_left(CTP_queue_folder):
                print('. ', end=' ')
                time.sleep(3)

            os.system(f"rm -r {os.path.join(CTP_import_folder, folder)}")

            try:
                new_folder = get_new_folder_id(CTP_output_folder, CTP_folder_list)
                CTP_folder_list.append(new_folder)

                file.write(f'{folder} {new_folder} {dateinc_value}\n')  # Modified line
                file.flush()
                print(f'{folder} {new_folder} {dateinc_value}\n')  # Modified line
            except Exception as e:
                print(f"An error occurred while processing {folder}: {e}")
                continue  # Stop or continue processin, folders should be checked manually

            end_time = time.time()
            elapsed_time = end_time - start_time
            expected_time_per_iteration = elapsed_time / (i+1)
            expected_total_time = expected_time_per_iteration * len(all_patient_folders)
            print(f"Expected total time: {expected_total_time} seconds")

            # Check for available disk space
            if not check_free_space(CTP_import_folder):
                print("Not enough free space on disk. Exiting.")
                sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
        subprocess.run(['pkill', '-f', 'java'])  # Terminate the CTP process if it's running
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        subprocess.run(['pkill', '-f', 'java'])  # Terminate the CTP process if it's running
        traceback.print_exc()
