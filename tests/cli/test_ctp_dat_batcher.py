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


def test_ctp_dat_batcher_script_basic(script_runner, test_dir, data_dir):

    cmd = [
        'tml_ctp_dat_batcher',
        "-i",
        os.path.join(data_dir, "PACSMANCohort"),
        "-o",
        os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-basic"),
        "-s",
        os.path.join(data_dir, "dat_scripts", "anonymizer.script"),
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
    ]

    ret = script_runner.run(cmd)
    assert ret.success
    assert ret.stderr == ''

    # Check that the output directory has been created
    assert os.path.exists(os.path.join(test_dir, "tmp", "PACSMANCohort-CTP-pacsman"))
