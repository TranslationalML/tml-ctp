# `TML-CTP`

This project aims to depersonalize imaging data. It is developed by the Translational Machine Learning Lab at the Lausanne University Hospital for internal use as well as for open-source software distribution. The project is not affiliated to the [RSNA](https://www.rsna.org) but builds upon their [imaging research tools](https://www.rsna.org/research/imaging-research-tools).

**DISCLAIMER: The few template scripts provided by `TML-CTP` are only for testing it with your application. They are not intended to be used in a clinical or research setting, and should be considered incomplete test samples. DICOM files filtered through this program and associated scripts are not guaranteed to be free of Protected Health Information (PHI).**

## Description

`TML-CTP` leverages the powerful RSNA MIRC [Clinical Trial Processor (CTP) DICOM anonymizer](https://mircwiki.rsna.org/index.php?title=MIRC_CTP) (Legacy Java version) to depersonalize imaging data by providing:
- the `tml-ctp-anonymizer` Docker image which encapsulates the Dicom Anonymizer Tool (DAT) of the Clinical Trial Processor (CTP)
- the `tml_ctp` Python package which batches the anonymization process via the Docker image
- a few template scripts for testing DAT.

Compared to the [legacy Java version of RSNA DICOM Anonymizer](https://github.com/johnperry/Anonymizer/), `TML-CTP` provides easier parallelisation based on Docker isolation, enables random date shifts per patient (as opposed to project-wide), as well as anonymization (as opposed to coding), whereby the link between patient identity and patient code is not reversible (which is the case with unsalted hashes). Please see if the more recent [Python version of RSNA DICOM Anonymizer](https://github.com/RSNA/Anonymizer) suits your use case better.

The project publishes for each version release:
- a new tagged Docker image to [quay.io](https://quay.io) as [quay.io/translationalml/tml-ctp-anonymizer](https://quay.io/repository/translationalml/tml-ctp-anonymizer/)
- a new Python package to the [Python Package Index](https://pypi.org/) as [tml_ctp](https://pypi.org/project/tml_ctp/).

## Pre-requisites

`TML-CTP` relies on the two main tools that has to be installed a-priori:

- `Docker`: Software containerization engine (See [Installation instructions](https://docs.docker.com/engine/install/))
- `Python 3.10` with `pip`.

## Installation

The installation of `TML_CTP` consists of the two following tasks:

1. Pull the `tml-ctp-anonymizer` image from `quay.io`:

  ```bash
  docker pull quay.io/translationalml/tml-ctp-anonymizer:1.1.1
  ```

2. In a Python 3.10 environment, install the Python package `tml_ctp` with `pip`:

  ```bash
  pip install tml_ctp==1.1.1
  ```
  
  This will install the main `tml_ctp_dat_batcher` script and a two other utility scripts (`tml_ctp_clean_series_tags` and `tmp_ctp_delete_identifiable_dicoms`) among with all Python dependencies.

You are ready to use `TML-CTP`!🚀

## How to use `tml_ctp_dat_batcher`

### Usage

```output
usage: tml_ctp_dat_batcher [-h] -i INPUT_FOLDERS -o OUTPUT_FOLDER -s DAT_SCRIPT [--new-ids NEW_IDS]
                           [--day-shift DAY_SHIFT] [--image-tag IMAGE_TAG] [--version]

Run DAT.jar (CTP DicomAnonymizerTool) with Docker to anonymize DICOM files.

options:
  -h, --help            show this help message and exit
  -i INPUT_FOLDERS, --input-folders INPUT_FOLDERS
                        Parent folder including all folders of files to be anonymized.
  -o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER
                        Folder where the anonymized files will be saved.
  -s DAT_SCRIPT, --dat-script DAT_SCRIPT
                        Script to be used for anonymization by the DAT.jar tool.
  --new-ids NEW_IDS     JSON file generated by pacsifier-get-pseudonyms containing the mapping between the
                        old and new patient IDs. It should follow the format {"old_id1": "new_id1",
                        "old_id2": "new_id2", ...}. If not provided, the script will generate a new ID
                        randomly.
  --day-shift DAY_SHIFT
                        JSON file containing the day shift / increment to use for each patient ID. The
                        old patient ID is the key and the day shift is the value, e.g. {"old_id1": 5,
                        "old_id2": -3, ...}. If not provided, the script will generate a new day shift
                        randomly.
  --image-tag IMAGE_TAG
                        Tag of the Docker image to use for running DAT.jar (default: tml-ctp-
                        anonymizer:<version>).
  --version             show program's version number and exit
```

### Examples

#### Basic

```bash
tml_ctp_dat_batcher \
  -i /path/to/input/folder \
  -o /path/of/output/folder \
  -s /path/to/dat/script
```
where:
- `/path/to/input/folder` should be structured as follows:

  ```
  /path/to/input/folder
  |__ sub-<patientID1>
  |     |__ ses-<sessionDate1>
  |     |     |__ Series1-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ Series2-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ ...
  |     |__ ses-<sessionDate2>
  |     |     |__ Series1-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ Series2-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ ...
  |     |_ ...
  |__ sub-<patientID2>
  |     |__ ses-<sessionDate1>
  |     |     |__ Series1-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ Series2-Description  # Can be any name
  |     |     |     |__ 001.dcm
  |     |     |     |__ 002.dcm
  |     |     |     |__ ...
  |     |     |__ ...
  ```

- `/path/of/output/folder` will keep the same structure but the patientIDs and sessionDates will be replaced by the new IDs and Dates
- `/path/to/dat/script` should point to the anonymizer script used by DAT. The doc for the syntax can be found here: <https://mircwiki.rsna.org/index.php?title=The_CTP_DICOM_Anonymizer>.


#### Advanced Usage with `--new-ids` and `--day-shift`

You can ensure consistency in the depersonalization process by providing JSON files generated by pacsifier-get-pseudonyms that set specific new patient IDs and day shifts for each patient, rather than relying on randomly generated values. 

```bash
tml_ctp_dat_batcher \
  -i /path/to/input/folder \
  -o /path/of/output/folder \
  -s /path/to/dat/script \
  --new-ids /path/to/new_ids.json \
  --day-shift /path/to/day_shift.json
```

## How to use `tml_ctp_clean_series_tags`

After running `tml_ctp_dat_batcher`, you may still need to make sure any PatientID or SeriesDate are not present in the DICOM tags at all level (such as in sequences). You can use `tml_ctp_clean_series_tags` for that.

### Usage

```output
usage: tml_ctp_clean_series_tags [-h] [--CTP_data_folder CTP_DATA_FOLDER] [--original_cohort ORIGINAL_COHORT]
                                 [--ids_file IDS_FILE]

Dangerous tags process and recursive overwrite of DICOM images.

options:
  -h, --help            show this help message and exit
  --CTP_data_folder CTP_DATA_FOLDER
                        Path to the CTP data folder.
  --original_cohort ORIGINAL_COHORT
                        Path to the original cohort folder.
  --ids_file IDS_FILE   Path to the IDs file generated byt the CTP batcher file.
```

## How to use `tml_ctp_delete_identifiable_dicoms`

After running `tml_ctp_dat_batcher`, you may still need to delete some files that may
  have burn-in patient data, such as dose reports, or visible face, such as T1w MPRAGEs.
You can use `delete_identifiable_dicoms.py` for that.

### Usage

```output
usage: tml_ctp_delete_identifiable_dicoms [-h] --in_folder IN_FOLDER [--delete_T1w] [--delete_T2w] [--pattern_dicom_files PATTERN]

Delete DICOM files that could lead to identifying the patient.

options:
  -h, --help            show this help message and exit
  --in_folder IN_FOLDER, -d IN_FOLDER
                        Root dir to the dicom files to be screened for identifiables files.
  --delete_T1w, -t1w    Delete potentially identifiable T1-weighted images such as MPRAGE
  --delete_T2w, -t2w    Delete potentially identifiable T2-weighted images such as FLAIR
  --pattern_dicom_files, -p    PATTERN_DICOM_FILES Pattern for the DICOM file structure inside patient folder.
```

###  Example 

```output
python delete_identifiable_dicoms.py \
  --in_folder /path/to/input/folder \
  --pattern_dicom_files "*/*/*.dcm" \
  --delete_T1w
```

## For Developers

### Extra pre-requisites

You will need `make` (See [official docs](https://www.gnu.org/software/make/) for installation) which is used by this project to ease the execution of the manual and CI/CD workflow tasks involved in the whole project software development life cycle. 

Note that `make` is a Linux tool. If you are on Windows, you will have to use the Windows Subsystem for Linux (WSL). See [WSL Installation instructions](https://learn.microsoft.com/en-us/windows/wsl/install).

#### List of `make` commands

```output
build-docker                   Builds the Docker image
install-python                 Install the python package with pip
install-python-all             Install the python package with all dependencies used for development
build-python-wheel             Build the python wheel
clean-python-build             Clean the python build directory
install-python-wheel           Install the python wheel
tests                          Run all tests
clean-tests                    Clean the directories generated by the pytest tests
help                           List available make command for this project
```

### Manual installation

Manual installation of `TML-CTP` consists of three following steps. In a terminal with Python `3.10` available: 

1. Clone this repository locally:

  ``````
  cd <preferred-installation-directory>
  git clone git@github.com:TranslationalML/tml-ctp.git
  cd tml-ctp
  ``````
   
2. Build the Docker image with `make`:

  ```
  make build-docker
  ```

3. Install all the Python development environment with `make`:

  ```
  make install-python-all
  ```
  
  This will install with `pip`:
  - all Python dependencies needed for development (such as `black` for the Python code formatter or `pytest` for the tests)
  - the package `tml_ctp` including its main `tml_ctp_dat_batcher` script and a few other utility scripts
  - all Python dependencies of the package.

You are ready to develop `TML-CTP`!🚀

### How to run the tests

For convenience you can run in a terminal with Python 3.10 available the following command:

```bash
make tests
```

which will take care of (1) re-building the Docker image if necessary, (2) cleaning the test directories, (3) re-installing the package with `pip`, and (4) executing the tests with `pytest`.

At the end, code coverage reports in different formats are generated and saved inside the `tests/report` directory.

## Funding

This project is partially funded by the [Lundin Family Brain Tumour Research Center](https://www.chuv.ch/en/braintumour/).

## Acknowledgments

We would like to thank Alexandre Wetzel and Augustin Augier for their valuable contributions to this project.

## Authors

This project was developed and maintained by the following contributors:

- **Sébastien Tourbier**
- **Jonathan Rafael Patino-Lopez**
- **Elodie Savary**
- **Jonas Richiardi**

## License

Copyright 2023-2024 Lausanne University and Lausanne University Hospital, Switzerland & Contributors

This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. 
If a copy of the MPL was not distributed with this file, You can obtain one at [http://mozilla.org/MPL/2.0/](http://mozilla.org/MPL/2.0/).

### Test Data License

The DICOM series files used for testing in this project are generated from the [PACSMAN_data](https://github.com/TranslationalML/PACSMAN_data) library.

These files are distributed under the **Creative Commons Attribution 4.0 International (CC BY 4.0) License**. For more information, please refer to the [test data README](tests/data/README.md) and the [CC BY 4.0 License](https://creativecommons.org/licenses/by/4.0/).
