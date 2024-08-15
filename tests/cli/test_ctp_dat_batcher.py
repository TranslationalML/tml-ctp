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

"""Define tests for the ctp_dat_batcher CLI script."""

import os
from tml_ctp.info import __container_name__, __version__
from unittest.mock import patch
from pathlib import Path
from tml_ctp.cli.ctp_dat_batcher import check_and_rename_dicom_files


def test_ctp_dat_batcher_script_basic(script_runner, test_dir, data_dir):

    cmd = [
        'tml_ctp_dat_batcher',
        "-i",
        os.path.join(data_dir, "PACSMANCohort"),
        "-o",
        os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-basic"),
        "-s",
        os.path.join(data_dir, "dat_scripts", "anonymizer.script"),
        "--image-tag",
        f"{__container_name__}:{__version__}",
    ]

    ret = script_runner.run(cmd)
    assert ret.success
    assert ret.stderr == ''

    # Check that the output directory has been created
    assert os.path.exists(os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-basic"))


def test_ctp_dat_batcher_script_pacsman(script_runner, test_dir, data_dir):
    
    cmd = [
        'tml_ctp_dat_batcher',
        "-i",
        os.path.join(data_dir, "PACSMANCohort"),
        "-o",
        os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-pacsman"),
        "-s",
        os.path.join(data_dir, "dat_scripts", "anonymizer.script"),
        "--new-ids",
        os.path.join(data_dir, "pacsman-get-pseudonyms", "new_ids_PACSMANCohort.json"),
        "--day-shift",
        os.path.join(data_dir, "pacsman-get-pseudonyms", "day_shift_PACSMANCohort.json"),
        "--image-tag",
        f"{__container_name__}:{__version__}",
    ]

    ret = script_runner.run(cmd)
    assert ret.success
    assert ret.stderr == ''

    # Check that the output directory has been created
    assert os.path.exists(os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-pacsman"))


@patch("os.walk")
@patch("pathlib.Path.rename")
@patch("pathlib.Path.with_name")
def test_check_and_rename_dicom_files(mock_with_name, mock_rename, mock_os_walk):
    """Test check_and_rename_dicom_files to ensure all DICOM files are renamed when any file contains a patient identifier.

    Raises:
        AssertionError: If the renaming logic does not work as expected.
    """
    dicom_folder = "/fake/path"
    patient_identifiers = {"JohnDoe", "JaneSmith"}
    replacement_string = "ANONYMOUS"

    # Mocking os.walk to return a list of files in the directory
    mock_os_walk.return_value = [
        ("/fake/path", [], ["JohnDoe.dcm", "JaneSmith_1.dcm", "normalfile.dcm"])
    ]

    # Mocking Path.with_name to return the new filename path
    mock_with_name.side_effect = lambda new_name: Path(f"/fake/path/{new_name}")

    # Call the function
    check_and_rename_dicom_files(dicom_folder, patient_identifiers, replacement_string)

    # Assert that Path.with_name was called correctly for all files
    mock_with_name.assert_any_call("ANONYMOUS.0.dcm")
    mock_with_name.assert_any_call("ANONYMOUS.1.dcm")
    mock_with_name.assert_any_call("ANONYMOUS.2.dcm")

    # Assert that Path.rename was called the expected number of times.
    # Currently, the function renames all files if any file contains a patient identifier. If the function is changed to rename only problematic files, this assertion will need to be updated accordingly.
    assert mock_rename.call_count == 3
    mock_rename.assert_any_call(Path("/fake/path/ANONYMOUS.0.dcm"))
    mock_rename.assert_any_call(Path("/fake/path/ANONYMOUS.1.dcm"))
    mock_rename.assert_any_call(Path("/fake/path/ANONYMOUS.2.dcm"))
