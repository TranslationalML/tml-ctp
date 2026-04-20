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
    """If identifiable data is present, deletes the Dicom file."""

    try:
        dataset = pydicom.read_file(filename)
    except pydicom.errors.InvalidDicomError:
        print(f"Dicom reading error at file at path: {filename}")
        raise

    delete_this_file = False

    attributes = dataset.dir("")
    if "Modality" in attributes and "SR" in dataset.data_element("Modality").value:
        delete_this_file = True

    if not delete_this_file and "ImageType" in attributes:
        if any(
            this_type in dataset.data_element("ImageType").value
            for this_type in IMAGETYPES_TO_REMOVE
        ):
            delete_this_file = True
        if "SECONDARY" in dataset.data_element("ImageType").value and "CT" in dataset.data_element("Modality").value:
            delete_this_file = True

    if not delete_this_file and "ProtocolName" in attributes:
        if re.search(r"(?i).*(Scout|localizer).*", dataset.data_element("ProtocolName").value):
            delete_this_file = True

    if not delete_this_file and "SeriesDescription" in attributes:
        if re.search(r"(?i).*(morpho|DEV).*", dataset.data_element("SeriesDescription").value):
            delete_this_file = True
        if re.search(r"(?i).*report.*", dataset.data_element("SeriesDescription").value):
            delete_this_file = True
        if re.search(r"(?i).*AAhead.*", dataset.data_element("SeriesDescription").value):
            delete_this_file = True
        if re.search(r"(?i).*rapid.*", dataset.data_element("SeriesDescription").value):
            delete_this_file = True
        if re.search(r"(?i).*KEY_IMAGES.*", dataset.data_element("SeriesDescription").value):
            delete_this_file = True

    if not delete_this_file and delete_T1w:
        if ("SequenceName" in attributes) and ("ImageType" in attributes):
            if any(
                this_seqname in dataset.data_element("SequenceName").value
                for this_seqname in T1W_TO_REMOVE
            ) and "ORIGINAL" in dataset.data_element("ImageType").value:
                delete_this_file = True

    if not delete_this_file and delete_T2w:
        if ("SequenceName" in attributes) and ("ImageType" in attributes):
            if "ir" in dataset.data_element("SequenceName").value and "ORIGINAL" in dataset.data_element("ImageType").value:
                delete_this_file = True

    if delete_this_file:
        os.remove(filename)

    return delete_this_file


def sanitize_all_dicoms_within_root_folder(
    datapath: str,
    pattern_dicom_files: str = "ses-*/*/*.dcm",
    delete_T1w: bool = False,
    delete_T2w: bool = False,
) -> int:
    """Sanitizes all DICOM images located at the datapath."""

    # Get all patient directories
    patients_folders = next(os.walk(datapath))[1]

    if not patients_folders:
        raise NotADirectoryError(
            "Each patient should have their own directory under the provided root " + datapath
        )

    for patient in tqdm(patients_folders):
        print(f"Processing {patient}")
        current_path = os.path.join(datapath, patient, pattern_dicom_files)
        all_filenames = glob(current_path)

        print(f"Searching for pattern: {current_path}")
        print(f"Found files: {all_filenames}")

        if not all_filenames:
            warnings.warn(f"Problem reading data for patient {patient} at {current_path}.")
            warnings.warn(f"Patient directories are expected to conform to the pattern {pattern_dicom_files}")
        else:
            n_deleted_files_in_series = 0

            for filename in all_filenames:
                file_deleted = delete_identifiable_dicom_file(filename, delete_T1w, delete_T2w)

                if file_deleted:
                    n_deleted_files_in_series += 1

            if n_deleted_files_in_series > 0:
                print(f"Deleted {n_deleted_files_in_series} files from series {current_path}")

    return 0


def get_parser():
    """Get parser object for script delete_identifiable_dicoms.py."""
    parser = argparse.ArgumentParser(
        description="Delete DICOM files that could lead to identifying the patient."
    )
    parser.add_argument(
        "--in_folder",
        "-d",
        help="Root directory containing the DICOM files to screen.",
        required=True,
    )
    parser.add_argument(
        "--pattern_dicom_files",
        "-p",
        help="Pattern for DICOM file structure. Default is 'ses-*/*/*'.",
        default="ses-*/" + "*" + "/*.dcm",
    )
    parser.add_argument(
        "--delete_T1w",
        "-t1w",
        help="Delete potentially identifiable T1-weighted images like MPRAGE.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--delete_T2w",
        "-t2w",
        help="Delete potentially identifiable T2-weighted images like FLAIR.",
        default=False,
        action="store_true",
    )
    return parser


def main():
    """Main function."""
    parser = get_parser()
    args = parser.parse_args()

    data_path = os.path.normcase(os.path.abspath(args.in_folder))
    pattern_dicom_files = args.pattern_dicom_files
    delete_T1w = args.delete_T1w
    delete_T2w = args.delete_T2w

    if not os.path.isdir(data_path):
        raise NotADirectoryError("Input directory does not exist.")

    print(f"Deleting potentially identifiable DICOM files within {data_path}")

    sanitize_all_dicoms_within_root_folder(
        datapath=data_path,
        pattern_dicom_files=pattern_dicom_files,
        delete_T1w=delete_T1w,
        delete_T2w=delete_T2w
    )


if __name__ == "__main__":
    main()
