#!/usr/bin/env python

# Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
