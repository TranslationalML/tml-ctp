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

"""Define tests for the clean_series_tags CLI script."""

import sys
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
