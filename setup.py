#!/usr/bin/env python

# Copyright (C) 2023, The TranslationalML team and Contributors. All rights reserved.
#  This software is distributed under the open-source Apache 2.0 license.

"""`Setup.py` for CTP DAT Batcher."""
from os import path as op
from setuptools import setup

from ctp_dat_batcher.info import (
    __version__,
    __packagename__
)


def main():
    """Main function of CTP DAT Batcher ``setup.py``"""
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
        name="ctp_dat_batcher",
        version=version,
        cmdclass=cmdclass,
    )


if __name__ == "__main__":
    main()
