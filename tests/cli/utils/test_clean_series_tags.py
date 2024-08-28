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


def test_clean_series_tags_script_basic(script_runner, test_dir, data_dir):

    test_dataset = "PACSMANCohort-clean_series_tags"
    # Copy the dataset to a temporary folder
    shutil.copytree(
        os.path.join(data_dir, "PACSMANCohort"),
        os.path.join(test_dir, "tmp", test_dataset),
    )

    test_ctp_dataset = "PACSMANCohort-CTP-clean_series_tags"
    # Copy the dataset to a temporary folder
    shutil.copytree(
        os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-basic"),
        os.path.join(test_dir, "tmp", test_ctp_dataset),
    )

    # Add SeriesDate to all dicom files in the test_dataset
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_dataset, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        ds.SeriesDate = "20230101"
        ds.save_as(dicom_file)

    # Add SeriesDate to all dicom files in the test_ctp_dataset
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_ctp_dataset, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        ds.SeriesDate = "20231008"
        ds.save_as(dicom_file)

    # Run the clean_series_tags script
    cmd = [
        "tml_ctp_clean_series_tags",
        "--CTP_data_folder",
        os.path.join(test_dir, "tmp", test_ctp_dataset),
        "--original_cohort",
        os.path.join(test_dir, "tmp", test_dataset),
        "--ids_file",
        os.path.join(
            test_dir,
            "tmp",
            test_ctp_dataset,
            "CTP_data_newids_dateinc_log.csv",
        ),
    ]

    ret = script_runner.run(cmd)

    # Check that the script has run successfully
    assert ret.success
    assert ret.stderr == ""

    # Check that the dicom files have been cleaned from any PatientID, PatientName
    # Original PatientID/PatientName : PACSMAN1
    dicom_files = glob.glob(
        os.path.join(test_dir, "tmp", test_ctp_dataset, "*", "*", "*", "*.dcm")
    )
    for dicom_file in dicom_files:
        ds = pydicom.dcmread(dicom_file)
        assert ds.PatientName != "PACSMAN1"
        assert ds.PatientID != "PACSMAN1"
        assert ds.SourcePatientGroupIdentificationSequence[0].PatientID != "PACSMAN1"


def test_clean_series_tags_script_basic_noseriesdate(script_runner, test_dir, data_dir):

    test_dataset = "PACSMANCohort-clean_series_tags_noseriesdate"
    # Copy the dataset to a temporary folder
    shutil.copytree(
        os.path.join(data_dir, "PACSMANCohort"),
        os.path.join(test_dir, "tmp", test_dataset),
    )

    test_ctp_dataset = "PACSMANCohort-CTP-clean_series_tags_noseriesdate"
    # Copy the dataset to a temporary folder
    shutil.copytree(
        os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-basic"),
        os.path.join(test_dir, "tmp", test_ctp_dataset),
    )

    # Run the clean_series_tags script
    cmd = [
        "tml_ctp_clean_series_tags",
        "--CTP_data_folder",
        os.path.join(test_dir, "tmp", test_ctp_dataset),
        "--original_cohort",
        os.path.join(test_dir, "tmp", test_dataset),
        "--ids_file",
        os.path.join(
            test_dir,
            "tmp",
            test_ctp_dataset,
            "CTP_data_newids_dateinc_log.csv",
        ),
    ]

    ret = script_runner.run(cmd)

    # Check that the script has run successfully
    assert ret.success
    assert ret.stderr == ""

    # Check that we have a all_file_issues.txt file created
    assert os.path.exists(
        os.path.join(test_dir, "tmp", test_ctp_dataset, "all_file_issues.txt")
    )

    # Check that content of all_file_issues.txt reports the missing SeriesDate
    with open(
        os.path.join(test_dir, "tmp", test_ctp_dataset, "all_file_issues.txt"), "r"
    ) as f:
        content = f.read()
    assert (
        """['original_ref_image.SeriesDate', 'ctp_ref_image.SeriesDate']"""
        in content.strip()
    )
