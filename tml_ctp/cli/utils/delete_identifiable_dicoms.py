#!/usr/bin/env python3

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

"""Delete DICOM files that could lead to identifying the patient."""

import argparse
import os
import re
import warnings
from glob import glob
import pydicom
from tqdm import tqdm


IMAGETYPES_TO_REMOVE = ["SCREEN SAVE", "DISPLAY", "LOCALIZER", "OTHER"]
T1W_TO_REMOVE = ["tfl3d", "fl2d"]


def delete_identifiable_dicom_file(
    filename: str, delete_T1w: bool = False, delete_T2w: bool = False
) -> bool:
    """If identifiable data is present, deletes the Dicom file.

    Args:
        filename (str): path to dicom image.
        delete_T1w (bool): also delete potentially identifiable (face-reconstructible) T1w images like MPRAGEs
        delete_T2w (bool): also delete potentially identifiable (face-reconstructible) T2w images like FLAIRs

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
        if "SR" in dataset.data_element("Modality").value:
            delete_this_file = True

    if not delete_this_file and ("ImageType" in attributes):
        if any(
            [
                this_type in dataset.data_element("ImageType").value
                for this_type in IMAGETYPES_TO_REMOVE
            ]
        ):
            delete_this_file = True
        if (
            "SECONDARY" in dataset.data_element("ImageType").value
            and "CT" in dataset.data_element("Modality").value
        ):
            delete_this_file = True

    if not delete_this_file and ("ProtocolName" in attributes):
        my_re_pn = re.compile("(?i).*(Scout|localizer).*")
        if my_re_pn.search(dataset.data_element("ProtocolName").value) is not None:
            delete_this_file = True

    if not delete_this_file and ("SeriesDescription" in attributes):
        my_re_sd_morpho = re.compile("(?i).*(morpho|DEV).*")
        if (
            my_re_sd_morpho.search(dataset.data_element("SeriesDescription").value)
            is not None
        ):
            delete_this_file = True
        # my_re_sd_tof=re.compile('(?i).*tof.*')
        # if my_re_sd_tof.search(dataset.data_element('SeriesDescription').value) is not None:
        #    delete_this_file = True
        my_re_sd_report = re.compile("(?i).*report.*")
        if (
            my_re_sd_report.search(dataset.data_element("SeriesDescription").value)
            is not None
        ):
            delete_this_file = True
        my_re_sd_AAH = re.compile("(?i).*AAhead.*")
        if (
            my_re_sd_AAH.search(dataset.data_element("SeriesDescription").value)
            is not None
        ):
            delete_this_file = True
        my_re_sd_rapid = re.compile("(?i).*rapid.*")  # RAPID results
        if (
            my_re_sd_rapid.search(dataset.data_element("SeriesDescription").value)
            is not None
        ):
            delete_this_file = True
        my_re_sd_Key = re.compile(
            "(?i).*KEY_IMAGES.*"
        )  # Key images - potentially annotated
        if (
            my_re_sd_Key.search(dataset.data_element("SeriesDescription").value)
            is not None
        ):
            delete_this_file = True

    if not delete_this_file and delete_T1w:
        # Sagittal 2D FLASH (Vida): SequenceName *fl2d1, ScanningSequence: GR, ImageType ORIGINAL\PRIMARY
        # mprage: ImageType ORIGINAL\PRIMARY, sequenceName tfl3d
        if ("SequenceName" in attributes) and ("ImageType" in attributes):
            if any(
                [
                    this_seqname in dataset.data_element("SequenceName").value
                    for this_seqname in T1W_TO_REMOVE
                ]
            ) and "ORIGINAL" in dataset.data_element("ImageType"):
                delete_this_file = True

    if not delete_this_file and delete_T2w:
        # Transverse 2D FLAIR (turbo inversion recovery): SequenceName *tir2d1_15, ScanningSequence: SE, MRAcquisitionType: 2D, ImageType ORIGINAL\PRIMARY
        # Other FLAIR: SequenceName: spcir, MRAcquisitionType: 3D
        # -> SequenceName: .*'?IR'?.* not case sensitive
        if ("SequenceName" in attributes) and ("ImageType" in attributes):
            if "ir" in dataset.data_element(
                "SequenceName"
            ).value and "ORIGINAL" in dataset.data_element("ImageType"):
                delete_this_file = True

    if delete_this_file:
        os.remove(filename)

    return delete_this_file


def sanitize_all_dicoms_within_root_folder(
    datapath: str,
    pattern_dicom_files: str = os.path.join("ses-*", "*", "*"),
    delete_T1w: bool = False,
    delete_T2w: bool = False,
) -> int:
    """Sanitizes all Dicom images located at the datapath in the structure specified by pattern_dicom_files parameter.

    Args :
        datapath (str): The path to the dicom images.
        pattern_dicom_files (str): the (generic) path to the dicom images starting from the patient folder.
                                   In a PACSMAN dump, this would reflect e.g. ses-20170115/0002-MPRAGE/*.dcm
        delete_T1w (bool): delete T1-weighted images that could be used to identify the patients
        delete_T2w (bool): delete T2-weighted images that could be used to identify the patients

    Returns :
        int : always 0
    """

    # List all  patient directories.
    patients_folders = next(os.walk(datapath))[1]

    if not patients_folders:
        raise NotADirectoryError(
            "Each patient should have their own directory under the provided root "
            + datapath
        )

    # Loop over patients...
    for _, patient in enumerate(tqdm(patients_folders)):
        print(f"processing {patient}")
        current_path = os.path.join(datapath, patient, pattern_dicom_files)

        # List all files within patient folder
        all_filenames = glob(current_path)

        if not all_filenames:
            warnings.warn(
                "Problem reading data for patient "
                + patient
                + " at "
                + current_path
                + "."
            )
            warnings.warn(
                "Patient directories are expect to conform to the pattern set "
                "in pattern_dicom_files, currently " + pattern_dicom_files
            )
        else:
            # List all study dirs for this patient.
            study_dirs = next(os.walk(os.path.join(datapath, patient)))[1]

            for study_dir in study_dirs:
                # List all series dirs for this patient.
                series_dirs = next(os.walk(os.path.join(datapath, patient, study_dir)))[
                    1
                ]

                # Loop over this patient's series one by one
                for series_dir in series_dirs:
                    all_filenames_series = glob(
                        os.path.join(datapath, patient, study_dir, series_dir, "*")
                    )

                    # Loop over all dicom files within a series and remove offending files
                    n_deleted_files_in_series = 0
                    for filename in all_filenames_series:
                        # TODO speedup - if we flag one file, we can assume the whole series can be deleted and we can
                        #  just delete the rest of the dir
                        file_deleted = delete_identifiable_dicom_file(
                            filename, delete_T1w, delete_T2w
                        )
                        if file_deleted:
                            n_deleted_files_in_series += 1

                    if n_deleted_files_in_series > 0:
                        print(
                            f"Deleted {n_deleted_files_in_series} files from series {series_dir}"
                        )
    return 0


def get_parser():
    """Get parser object for script delete_identifiable_dicoms.py."""
    parser = argparse.ArgumentParser(
        description="Delete DICOM files that could lead to identifying the patient."
    )
    parser.add_argument(
        "--in_folder",
        "-d",
        help="Root dir to the dicom files to be screened for identifiables files.",
        required=True,
    )
    parser.add_argument(
        "--delete_T1w",
        "-t1w",
        help="Delete potentially identifiable T1-weighted images such as MPRAGE",
        default=False,
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "--delete_T2w",
        "-t2w",
        help="Delete potentially identifiable T2-weighted images such as FLAIR",
        default=False,
        required=False,
        action="store_true",
    )
    return parser


def main():
    """Main function of the `delete_identifiable_dicoms.py` script."""
    # Parse command-line arguments
    parser = get_parser()
    args = parser.parse_args()

    data_path = os.path.normcase(os.path.abspath(args.in_folder))
    delete_T1w = args.delete_T1w
    delete_T2w = args.delete_T2w

    if not os.path.isdir(data_path):
        raise NotADirectoryError("Input directory does not exist.")

    print(
        "Deleting potentially identifiable Dicom files within path {}".format(
            os.path.abspath(data_path)
        )
    )
    # Sanitize all files.
    _ = sanitize_all_dicoms_within_root_folder(
        datapath=data_path, delete_T1w=delete_T1w, delete_T2w=delete_T2w
    )


if __name__ == "__main__":
    main()
