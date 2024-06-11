import os
import pydicom as dicom
import pandas as pd
import re
from os import walk

import argparse

def get_process_images_parser():
    parser = argparse.ArgumentParser(
        "process_images: ....\n Don't forget to use this cmd before: conda activate tlm-ctp",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Specify an output directory to save the file"
    )
    parser.add_argument(
        "-x",
        "--excel",
        type=str,
        required=True,
        help="The Excel file containing the path to transform -> ex: clmpacsmolis_exam_with_code3.xlsx"
    )

    return parser
def main():
    parser = get_process_images_parser()
    args = parser.parse_args()

    dest= os.path.abspath(args.output)
    #"/data/extraction/dsrsd-1183/CLM_TMP_arben_4"

    dict = pd.read_excel(args.excel, engine='openpyxl')
    print(dict.head())
    d1 = dict[['PATH']]

    for index, row  in d1.iterrows():
        print(row['PATH'])
        path = row['PATH']
        #path = row['PATH'].replace("//filearc/data/CRN/CLM/Images/DICOM","/data/extraction/dsrsd-1183/CLM")
        #path = 'C:\\DATA\\1.2.826.0.1.3680043.2.146.2.20.38735.1500076513.0'
        # Three digit number followed by space followed by two digit number
        pattern = '.*/sub-\d+/ses-\d+'

        # match variable contains a Match object.
        match = re.search(pattern, path)

        if match:
            sp = path.split("/")
            print(sp)
            dd=dest+"/"+sp[-2]
            if not os.path.exists(dd):
                 os.makedirs(dd)
                 os.system(f"chmod 777 {dd}")
            dd=dd+"/"+sp[-1]
            cmd = "ln -s "+path +" "+dd
            print(cmd)
            os.system(cmd)

        else:
            #print("pattern not found")
            #get first file
            ready=False
            for (dirpath, dirnames, filenames) in walk(path):
                if ready:
                    break
                for f in filenames:
                    if ready:
                        break
                    try:
                        ds = dicom.dcmread(dirpath+"/"+f)
                        sub = f"sub-{ds[0x0010,0x0020].value}"
                        time = ds[0x0008,0x0030].value
                        time = time[:6]
                        ses = f"ses-{ds[0x0008,0x0020].value}{time}"
                        ll = path.split("/")
                        ll = ll[-1]
                        ready = True
                    except:
                        print(f"error reading {f}")

            dd = dest+"/"+sub
            if not os.path.exists(dd):
                os.makedirs(dd)
                os.system(f"chmod 777 {dd}")
            dd=dd+"/"+ses
            if not os.path.exists(dd):
                os.makedirs(dd)
                cmd = "ln -s " + path + " " + dd
                print(cmd)
                os.system(cmd)
            else:
                print(f'''###########################################################\n
    dupplicate error on \n
    src:{path}\n
    dest:{dd}\n
    ####################################################################
    ''')
        #cmd2 = f"tml_ctp_dat_batcher -i {dd} -o {result} -s /data/git-src/tml-ctp/dat_scripts/DicomAnonymizer_Whitelist_extended.script --new-ids /data/extraction/dsrsd-1183/new_ids_PACS-MOLIS.json --day-shift /data/extraction/dsrsd-1183/day_shift_PACS-MOLIS.json"
        #print(cmd2)
        #os.system(cmd2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
