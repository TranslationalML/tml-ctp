
import argparse
import os
import re
import sys
import warnings

from glob import glob

import pydicom
from tqdm import tqdm

IMAGETYPES_TO_REMOVE=['SCREEN SAVE','DISPLAY','LOCALIZER','OTHER']


def delete_identifiable_dicom_file(
        filename: str) -> bool:
    """
    If identifiable data is present, deletes the Dicom file

    Args :
        filename: path to dicom image.

    Returns:
        bool: whether the file was deleted (True) or not (False)

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

    # parse DICOM header
    attributes = dataset.dir("")
    if "Modality" in attributes:
        if 'SR' in dataset.data_element('Modality').value:
            delete_this_file = True

    if not delete_this_file and ("ImageType" in attributes):
        if any([this_type in dataset.data_element('ImageType').value for this_type in IMAGETYPES_TO_REMOVE]):
            delete_this_file = True
        if 'SECONDARY' in dataset.data_element('ImageType').value and 'CT' in dataset.data_element('Modality').value:
            delete_this_file = True

    if not delete_this_file and ("ProtocolName" in attributes):
        my_re_pn=re.compile('(?i).*(Scout|localizer|t2_haste_sag_ipat2).*')
        if my_re_pn.search(dataset.data_element('ProtocolName').value) is not None:
            delete_this_file = True

    if not delete_this_file and ("SeriesDescription" in attributes):
        my_re_sd_morpho=re.compile('(?i).*(morpho|DEV).*')
        if my_re_sd_morpho.search(dataset.data_element('SeriesDescription').value) is not None:
            delete_this_file = True
        #my_re_sd_tof=re.compile('(?i).*tof.*')
        #if my_re_sd_tof.search(dataset.data_element('SeriesDescription').value) is not None:
        #    delete_this_file = True
        my_re_sd_report = re.compile('(?i).*report.*')
        if my_re_sd_report.search(dataset.data_element('SeriesDescription').value) is not None:
            delete_this_file = True
        my_re_sd_AAH = re.compile('(?i).*AAhead.*')
        if my_re_sd_AAH.search(dataset.data_element('SeriesDescription').value) is not None:
            delete_this_file = True
        my_re_sd_rapid = re.compile('(?i).*rapid.*') # RAPID results
        if my_re_sd_rapid.search(dataset.data_element('SeriesDescription').value) is not None:
            delete_this_file = True
        my_re_sd_Key = re.compile('(?i).*KEY_IMAGES.*') # Key images - potentially annotated
        if my_re_sd_Key.search(dataset.data_element('SeriesDescription').value) is not None:
            delete_this_file = True

    if delete_this_file:
        os.remove(filename)

    return delete_this_file


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

                # Loop over this patient's series one by one
                for series_dir in series_dirs:
                    all_filenames_series = glob(os.path.join(datapath, patient, study_dir,series_dir,'*'))

                    # Loop over all dicom files within a series and remove offending files
                    n_deleted_files_in_series = 0
                    for filename in all_filenames_series:
                        file_deleted = delete_identifiable_dicom_file(filename)
                        if file_deleted:
                            n_deleted_files_in_series += 1

                    if n_deleted_files_in_series > 0:
                        print(f"Deleted {n_deleted_files_in_series} files from series {series_dir}")
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
