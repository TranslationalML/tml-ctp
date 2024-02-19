
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
