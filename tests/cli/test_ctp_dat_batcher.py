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
import pytest
from tml_ctp.info import __container_name__, __version__
from tml_ctp.cli.ctp_dat_batcher import update_dat_script_file


@pytest.fixture
def original_dat_script(tmp_path):
    """Fixture to create a temporary DAT script file with a basic structure for testing.

    This fixture creates a DAT script file in a temporary directory with only the DATEINC element
    on the second line and no PatientID or PatientName elements. The file is written to a path
    within the temporary directory provided by the `tmp_path` fixture.

    Args:
        tmp_path (pathlib.Path): A pytest fixture that provides a temporary directory unique to the test
                                 invocation, used to safely create temporary files and directories.

    Returns:
        pathlib.Path: The path to the created DAT script file.

    """
    original_dat_script_path = tmp_path / "original_dat_script.script"
    with open(original_dat_script_path, "w") as f:
        f.write("<script>\n")
        f.write(' <p t="DATEINC">-26</p>\n')  # Second line for DATEINC
        f.write("</script>\n")
    return original_dat_script_path


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


def test_update_dat_script_field_insert(original_dat_script, tmp_path):
    """Test that the update_dat_script_file function correctly appends the PatientID and PatientName
    elements before the closing </script> tag in the DAT script file when they are not already present.

    This test creates a minimal DAT script with only the DATEINC element and no PatientID or PatientName.
    It then runs the update_dat_script_file function.
    The test verifies that these elements are added before the closing </script>
    tag and that the DATEINC element keeps the correct position.

    Args:
        original_dat_script (pathlib.Path): Fixture providing the path to a temporary DAT script file
                                             without PatientID and PatientName.
        tmp_path (pathlib.Path): Fixture providing a temporary directory for writing the updated DAT script.

    Asserts:
        - PatientID is inserted before the </script> tag.
        - PatientName is inserted before the </script> tag.
        - DATEINC remains correctly placed in the second line.
    """
    # Run the function to update the script
    new_patient_id, new_patient_name, dateinc, new_dat_script = update_dat_script_file(
        str(original_dat_script), str(tmp_path)
    )

    # Read the modified script
    with open(new_dat_script, "r") as f:
        lines = f.readlines()

    # Find the index of the </script> tag
    end_script_index = next(i for i, line in enumerate(lines) if '</script>' in line)

    # Check that PatientID and PatientName are present before the </script> tag
    assert any('n="PatientID"' in line for line in lines[:end_script_index]), "PatientID not found before </script> tag"
    assert any('n="PatientName"' in line for line in lines[:end_script_index]), "PatientName not found before </script> tag"

    # Verify DATEINC is correctly placed in the second line
    assert f'<p t="DATEINC">{dateinc}</p>' in lines[1]
