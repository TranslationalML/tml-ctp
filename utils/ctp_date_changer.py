#!/usr/bin/env python3

# Copyright (C) 2023, The TranslationalML team and Contributors. All rights reserved.
#  This software is distributed under the open-source Apache 2.0 license.

"""Script to be added before or IN CTP batcher to change the date of the DICOM files."""

import random
import xml.etree.ElementTree as ET

if __name__ == "__main__":
    # load thet .script file
    tree = ET.parse('DICOM_Whitelisting_MasterProfile_CTP_20210507/DicomAnonymizer_Whitelist.script')
    # find the DATEINC tag
    dateinc_tag = tree.find(".//*[@t='DATEINC']")
    # generate a random number between a certain range
    rand_num = random.randint(0, 30)  # replace with your desired range
    dateinc_tag.text = str(rand_num)
    tree.write('DICOM_Whitelisting_MasterProfile_CTP_20210507/DicomAnonymizer_Whitelist_2.script')
