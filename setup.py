#!/usr/bin/env python

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

"""`Setup.py` for TML-CTP."""

from os import path as op
from setuptools import setup

from tml_ctp.info import (
    __version__,
    __packagename__
)


def main():
    """Main function of TML-CTP ``setup.py``"""
    root_dir = op.abspath(op.dirname(__file__))

    version = None
    cmdclass = {}
    if op.isfile(op.join(root_dir, __packagename__, "VERSION")):
        with open(op.join(root_dir, __packagename__, "VERSION")) as vfile:
            version = vfile.readline().strip()

    if version is None:
        version = __version__

    # Setup configuration
    setup(
        name="tml_ctp",
        version=version,
        cmdclass=cmdclass,
    )


if __name__ == "__main__":
    main()
