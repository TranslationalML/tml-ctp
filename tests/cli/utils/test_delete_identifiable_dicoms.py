# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Define tests for the clean_series_tags CLI script."""

import os
import shutil
import glob
import pydicom
import pandas as pd


def test_delete_identifiable_dicoms_script_basic(script_runner, test_dir, data_dir):

    test_dataset = "PACSMANCohort-delete_identifiable_dicoms"
    # Copy the dataset to a temporary folder
    shutil.copytree(
        os.path.join(data_dir, "PACSMANCohort"),
        os.path.join(test_dir, "tmp", test_dataset),
    )

    # Add missing SequenceName to all dicom files in the test_dataset
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_dataset, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        ds.SequenceName = "tfl3d"
        ds.save_as(dicom_file)

    # Run the clean_series_tags script
    cmd = [
        "tml_ctp_delete_identifiable_dicoms",
        "--in_folder",
        os.path.join(test_dir, "tmp", test_dataset),
        "-t1w",
    ]

    ret = script_runner.run(cmd)

    # Check that the script has run successfully
    assert ret.success

    assert "Deleted 128 files" in ret.stdout

    # Check that all dicom files have been deleted as SequenceName is tfl3d 
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_dataset, "*", "*", "*", "*.dcm")
    )
    assert len(dicom_files) == 0
