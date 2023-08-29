from ast import AST
import sys, os
import os.path
import time
import subprocess
import random
import re

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
    subprocess.Popen(['java', '-jar', ctp_runner])

def update_config_file(original_config):
    with open(original_config, 'r') as f:
        lines = f.readlines()

    # Assuming the DATEINC is always at the second line
    dateinc_value = random.randint(-30, 30)
    lines[1] = f' <p t="DATEINC">{dateinc_value}</p>\n'

    with open(original_config, 'w') as f:
        f.writelines(lines)


def main():
    start_time = time.time()
    first_time = True  # To track if CTP has been launched already
    input_folders = '/media/jonathan/WDelements/ASTRAL/'
    CTP_import_folder = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/import/'
    CTP_queue_folder  = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/queue/'
    CTP_output_folder = '/home/jonathan/Apps/CTP/roots/DirectoryStorageService/'
    original_config = '/home/jonathan/Apps/CTP/scripts/DicomAnonymizer_Whitelist_extended.script'
    ctp_runner = '/home/jonathan/Apps/CTP/Runner.jar'
    # Switch to the necessary directory
    os.chdir("/home/jonathan/Apps/CTP/")

    all_patient_folders = [dir for dir in os.listdir(input_folders) if os.path.isdir(os.path.join(input_folders, dir))]
    all_patient_folders.sort()

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
    except FileNotFoundError:
        pass

    with open(ASTRAL_CTP_ids_file, 'a') as file:
        for i, folder in enumerate(all_patient_folders):
            if last_processed_folder and folder <= last_processed_folder:
                continue

            # Update the configuration file with a new random DATEINC
            update_config_file(original_config)

            # Relaunch the CTP Runner to use the new configuration
            launch_ctp_runner(ctp_runner, first_time)

            os.system(f"cp -r {os.path.join(input_folders, folder)} {CTP_import_folder}")

            print(f'Processing {folder} [{i+1}/{len(all_patient_folders)}]')
            
            while is_there_files_left(CTP_import_folder) or is_there_files_left(CTP_queue_folder):
                print('. ', end=' ')
                time.sleep(3)

            os.system(f"rm -r {os.path.join(CTP_import_folder, folder)}")

            try:
                new_folder = get_new_folder_id(CTP_output_folder, CTP_folder_list)
                CTP_folder_list.append(new_folder)

                file.write(f'{folder} {new_folder}\n')
                file.flush()
                print(f'{folder} {new_folder}\n')
            except Exception as e:
                print(f"An error occurred while processing {folder}: {e}")
                break  # Stop processing further folders should be rested manually

            end_time = time.time()
            elapsed_time = end_time - start_time
            expected_time_per_iteration = elapsed_time / (i+1)
            expected_total_time = expected_time_per_iteration * len(all_patient_folders)
            print(f"Expected total time: {expected_total_time} seconds")

            if(i>10):
                break

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
        subprocess.run(['pkill', '-f', 'java'])  # Terminate the CTP process if it's running
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        subprocess.run(['pkill', '-f', 'java'])  # Terminate the CTP process if it's running
    