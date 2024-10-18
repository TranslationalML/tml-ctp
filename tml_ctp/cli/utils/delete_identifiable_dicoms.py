#!/usr/bin/env python3

# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
    folder_depth: int = 3,
    delete_T1w: bool = False,
    delete_T2w: bool = False,
) -> int:
    """
    Sanitizes all Dicom images located at the datapath in the structure specified by the folder depth.

    Args:
        datapath (str): The path to the dicom images.
        folder_depth (int): The number of folder levels before reaching the DICOM files. Default is 3.
        delete_T1w (bool): Delete T1-weighted images that could be used to identify the patients.
        delete_T2w (bool): Delete T2-weighted images that could be used to identify the patients.

    Returns:
        int: Always 0.
    """
    # Generate the pattern based on the depth provided
    pattern_dicom_files = os.path.join(datapath, *(["*"] * folder_depth), "*.dcm")

    # Find all DICOM files based on the depth
    all_dicom_files = glob(pattern_dicom_files)

    if not all_dicom_files:
        warnings.warn(
            f"No DICOM files found at the provided depth {folder_depth}. "
            "Please check the folder structure or depth value."
        )
        return 0

    # Initialize dictionary to count deleted files per series
    deleted_files_per_series = {}

    # Process each DICOM file
    for dicom_file in all_dicom_files:
        series_dir = os.path.dirname(dicom_file)  # The folder where the DICOM file is located

        # Delete identifiable DICOM file
        file_deleted = delete_identifiable_dicom_file(dicom_file, delete_T1w, delete_T2w)

        if file_deleted:
            # Keep track of the number of deleted files per series
            if series_dir not in deleted_files_per_series:
                deleted_files_per_series[series_dir] = 0
            deleted_files_per_series[series_dir] += 1

    # Print results of deleted files per series
    for series_dir, n_deleted_files in deleted_files_per_series.items():
        print(f"Deleted {n_deleted_files} files from series {series_dir}")

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
    
    parser.add_argument(
        "--folder_depth",
        "-fd",
        help="Specify the depth of the DICOM folder (number of subdirectories). Default is 3.",
        type=int,
        default=3
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
    folder_depth = args.folder_depth  # Capture the folder depth argument

    if not os.path.isdir(data_path):
        raise NotADirectoryError("Input directory does not exist.")

    print(
        "Deleting potentially identifiable Dicom files within path {}".format(
            os.path.abspath(data_path)
        )
    )
    # Sanitize all files.
    _ = sanitize_all_dicoms_within_root_folder(
        datapath=data_path, folder_depth=folder_depth, delete_T1w=delete_T1w, delete_T2w=delete_T2w
    )


if __name__ == "__main__":
    main()
