
import argparse
import os
import re
import sys
import warnings

from glob import glob

import pydicom
from tqdm import tqdm

def delete_identifiable_dicom_file(
        filename: str) -> None:
    """
    If identifiable data is present, deletes the Dicom file

    Args :
        filename: path to dicom image.

    TODO:
        - Implement proper exception handling
    """

    # Load the current dicom file to depersonalise
    try:
        dataset = pydicom.read_file(filename)
    except pydicom.errors.InvalidDicomError:
        print("Dicom reading error at file at path :  " + filename)
        raise

    delete_this_file = False
    attributes = dataset.dir("")
    if "ImageType" in attributes:
        if 'SCREEN SAVE' in dataset.data_element('ImageType').value:
            delete_this_file = True
        if 'SECONDARY' in dataset.data_element('ImageType').value and 'CT' in dataset.data_element('Modality').value:
            delete_this_file = True
    if "Modality" in attributes:
        if 'SR' in dataset.data_element('Modality').value:
            delete_this_file = True
    if "ProtocolName" in attributes:
        my_re_pn=re.compile('(?i).*(Scout|localizer|t2_haste_sag_ipat2).*')
        if my_re_pn.search(dataset.data_element('ProtocolName').value) is not None:
            delete_this_file = True

    if delete_this_file:
        os.remove(filename)


def sanitize_all_dicoms_within_root_folder(
        datapath: str = os.path.join(".", "data"),
        pattern_dicom_files: str = os.path.join("ses-*", "*", "*")
    ) -> int:
    """
    Sanitizes all Dicom images located at the datapath in the structure specified by pattern_dicom_files parameter.
    Args :
        datapath: The path to the dicom images.
        pattern_dicom_files: the (generic) path to the dicom images starting from the patient folder. In a PACSMAN dump, this would reflect e.g.
            ses-20170115/0002-MPRAGE/*.dcm
    Returns :
        int : always 0
    """

    # List all  patient directories.
    patients_folders = next(os.walk(datapath))[1]

    if not patients_folders:
        raise NotADirectoryError('Each patient should have their own directory under the provided root ' + datapath)

    # Loop over patients...
    for patient_index, patient in enumerate(tqdm(patients_folders)):
        print(f"processing {patient}")
        current_path = os.path.join(datapath, patient, pattern_dicom_files)

        # List all files within patient folder
        all_filenames = glob(current_path)

        if not all_filenames:
            warnings.warn('Problem reading data for patient ' + patient + ' at ' + current_path + '.')
            warnings.warn('Patient directories are expect to conform to the pattern set '
                          'in pattern_dicom_files, currently ' + pattern_dicom_files)
        else:
            # List all study dirs for this patient.
            study_dirs = next(os.walk(os.path.join(datapath, patient)))[1]

            for study_dir in study_dirs:
                # List all series dirs for this patient.
                series_dirs = next(os.walk(os.path.join(datapath, patient, study_dir)))[1]

                for series_dir in series_dirs:
                    all_filenames_series = glob(os.path.join(datapath, patient, study_dir,series_dir,'*'))

                    # Loop over all dicom files within a patient directory and remove offending files
                    for filename in all_filenames_series:
                        delete_identifiable_dicom_file(filename)
    return 0
def main(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument("--in_folder", "-d", help="Root dir to the dicom files to be screened for identifiables files.",
                        default=os.path.join(".", "data"), required=True)

    args = parser.parse_args()

    data_path = os.path.normcase(os.path.abspath(args.in_folder))

    if not os.path.isdir(data_path):
        raise NotADirectoryError('Input directory does not exist.')

    print("Deleting potentially identifiable Dicom files within path {}".format(os.path.abspath(data_path)))
    # Sanitize all files.
    result = sanitize_all_dicoms_within_root_folder(datapath=data_path)

if __name__ == "__main__":
    main(sys.argv[1:])
