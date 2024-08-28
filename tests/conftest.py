# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Main conftest.py file which defines some fixtures and configuration for the tests."""

import os
import pytest


@pytest.fixture(scope="session")
def test_dir():
    """Return the path to the tests directory."""
    return os.path.dirname(__file__)


@pytest.fixture(scope="session")
def data_dir(test_dir):
    """Return the path to the data directory."""
    return os.path.join(test_dir, "data")
