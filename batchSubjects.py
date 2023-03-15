# Import required modules
from ast import AST
import sys, os
import os.path
import time

# Define a function to check if there are files left in a given folder
def isThereFilesLeftQuestionMark(path):
    for r, d, f in os.walk(path):
        for file in f:
            return True
    return False

# Define a function to get a new folder ID for a given folder
def getNewFolderID(CTP_output_folder,previous_folders):
    folder = [dir for dir in os.listdir(CTP_output_folder) if os.path.isdir(os.path.join(CTP_output_folder,dir)) and dir not in previous_folders]
    return folder[0]

# Define the input and output folders
input_folders = '//media/jonathan/DATA_SSD/ASTRAL_tmp/'
CTP_import_folder = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/import/'
CTP_queue_folder  = '/home/jonathan/Apps/CTP/roots/DirectoryImportService/queue/'
CTP_output_folder = '/home/jonathan/Apps/CTP/roots/DirectoryStorageService/'

# Read the list of all patient folders in the input folder and sort them
all_patient_folders = [dir for dir in os.listdir(input_folders) if os.path.isdir(os.path.join(input_folders,dir))]
all_patient_folders.sort()

# Read the list of all patient folders in the CTP output folder
CTP_folder_list    = [dir for dir in os.listdir(CTP_output_folder) if os.path.isdir(os.path.join(CTP_output_folder,dir))]

# Define the output file for the mapping between the old and new folder names
ASTRAL_CTP_ids_file = f"ASTRAL_CTP_{input_folders.split('/')[-2]}_ids.txt"
file = open(ASTRAL_CTP_ids_file,'w')

# Loop over each patient folder in the input folder
for i,folder in enumerate(all_patient_folders):
    # Copy the patient folder to the CTP import folder
    os.system(f"cp -r {os.path.join(input_folders,folder)} {CTP_import_folder}")
    print(f'Processing {folder} [{i}/{len(all_patient_folders)}]')
    # Wait until all files are processed by CTP
    while(isThereFilesLeftQuestionMark(CTP_import_folder) or isThereFilesLeftQuestionMark(CTP_queue_folder)):
        print('. ')
        time.sleep(30)

    # Remove the patient folder from the CTP import folder
    os.system(f"rm -r {os.path.join(CTP_import_folder,folder)}")

    # Generate a new folder name for the patient in the CTP output folder
    new_folder = getNewFolderID(CTP_output_folder,CTP_folder_list)
    CTP_folder_list.append(new_folder)

    # Write the mapping between the old and new folder names to the output file
    file.write(f'{folder} {new_folder}\n')
    print(f'{folder} {new_folder}\n')

# Close the output file
file.close()