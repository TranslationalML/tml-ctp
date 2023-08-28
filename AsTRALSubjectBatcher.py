from ast import AST
import sys, os
import os.path
import time

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

def main():
    start_time = time.time()

    input_folders = '/media/jonathan/WDelements/ASTRAL_only_folders/'
    CTP_import_folder = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/import/'
    CTP_queue_folder  = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/queue/'
    CTP_output_folder = '/home/jonathan/Apps/CTP/roots/DirectoryStorageService/'

    all_patient_folders = [dir for dir in os.listdir(input_folders) if os.path.isdir(os.path.join(input_folders, dir))]
    all_patient_folders.sort()

    CTP_folder_list = [dir for dir in os.listdir(CTP_output_folder) if os.path.isdir(os.path.join(CTP_output_folder, dir))]

    ASTRAL_CTP_ids_file = f"ASTRAL_CTP_{input_folders.split('/')[-2]}_ids.txt"

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
            except:
                print(f'{folder} already in the list (probably)')

            end_time = time.time()
            elapsed_time = end_time - start_time
            expected_time_per_iteration = elapsed_time / (i+1)
            expected_total_time = expected_time_per_iteration * len(all_patient_folders)
            print(f"Expected total time: {expected_total_time} seconds")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
