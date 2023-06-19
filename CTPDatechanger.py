#To be added before or IN  CTP batcher.

import random
import xml.etree.ElementTree as ET

# load thet .script file
tree = ET.parse('DICOM_Whitelisting_MasterProfile_CTP_20210507/DicomAnonymizer_Whitelist.script')
# find the DATEINC tag
dateinc_tag = tree.find(".//*[@t='DATEINC']")
# generate a random number between a certain range
rand_num = random.randint(0, 30)  # replace with your desired range
dateinc_tag.text = str(rand_num)
tree.write('DICOM_Whitelisting_MasterProfile_CTP_20210507/DicomAnonymizer_Whitelist_2.script')
