import pathlib
import shutil
from distutils.dir_util import copy_tree

from concurrent.futures import wait
import concurrent.futures
import os

from random import randint

import argparse

def get_process_images_parser():
    parser = argparse.ArgumentParser(
        "process_images: ....\n Don't forget to use this cmd before: conda activate tlm-ctp",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-s",
        "--src",
        type=str,
        required=True,
        help="The path to start exploring.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Specify an output directory to save the file"
    )
    parser.add_argument(
        "-t",
        "--thread",
        type=int,
        required=False,
        default=5,
        help="Specify the nbr of thread to execute the code"
    )

    return parser

def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

def worker(args):
   d = args[0]
   file_arc = args[1]
   dest_processed = args[2]
   output = args[3]

   tmpname = random_with_N_digits(8)
   tmpname = int(tmpname)
   sub=d.replace(file_arc,'')
   d1=f'{output}/tmp_{tmpname}'
   dd=f'{d1}/src{sub}'
   print(dd)
   if os.path.exists(dd):
      shutil.rmtree(dd)
   os.makedirs(dd)
   print("Copying file")
   copy_tree(d, dd)
   print("Anonymise")
   cmd=f'tml_ctp_dat_batcher -i {d1}/src -o {d1}/dep/ -s /data/git-src/tml-ctp/dat_scripts/DicomAnonymizer_Whitelist_extended.script --new-ids /data/extraction/dsrsd-1183/new_ids_PACS-MOLIS.json --day-shift /data/extraction/dsrsd-1183/day_shift_PACS-MOLIS.json > {d1}{sub}.log'
   print(cmd)
   result=os.system(cmd)
   if result == 0:
      print("Deperso ok")
      #move log
      shutil.move(f"{d1}{sub}.log", f"{output}/{sub}.log")
      #move depersonalisation
      if os.system(f"rsync -azh --remove-source-files {d1}/dep/* {output}/.")==0:
         shutil.rmtree(d1)
         os.system(f"mv {d} {dest_processed}/")
      else:
         print(f"Error on copying result from {d1}/dep/* to {output}/.")

def main():
    parser = get_process_images_parser()
    args = parser.parse_args()

    file_arc = os.path.abspath(args.src)
    #'/data/extraction/dsrsd-1183/CLM_TMP_arben_4'
    output = os.path.abspath(args.output)
    #'/data/extraction/dsrsd-1183/CLM_DSR/PRE_CTP_arben_7'
    nbThread = args.thread
    dest_processed = file_arc + "_processed"

    if not os.path.exists(output):
       os.makedirs(output)

    desktop = pathlib.Path(file_arc)
    print(desktop)

    subfolders = [ f.path for f in os.scandir(file_arc) if f.is_dir() ]

    print("Start")

    if not os.path.exists(dest_processed):
        os.makedirs(dest_processed)

    s1 = []
    for s in subfolders:
        s1.append((s,file_arc,dest_processed,output))

    #remove all tmp_ folder
    folders_rm = [f.path for f in os.scandir(output) if f.is_dir() and 'tmp_' in f.name]
    for fld in folders_rm:
        print(f"removing folder: {fld}")
        shutil.rmtree(fld)

    with concurrent.futures.ThreadPoolExecutor(max_workers=nbThread) as executor:
       for _ in executor.map(worker, s1):
          pass
       print('Waiting for tasks to complete...')
       # shutdown the pool, returns after all scheduled and running tasks complete
       executor.shutdown(wait=True)
       print("download and sort finished")

    print("finished")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
