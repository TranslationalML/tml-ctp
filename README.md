# Depersonalisation tools

Tools, whilelists, blacklists, configuration files for depersonalising imaging data.

## Getting started

The RSNA MIRC Clinical Trial Processor (CTP) DICOM anonymiser is the core engine. CTP doc is here: <https://mircwiki.rsna.org/index.php?title=MIRC_CTP> and the doc for the syntax for the anonymiser script is here: <https://mircwiki.rsna.org/index.php?title=The_CTP_DICOM_Anonymizer>.

## Depersonalising data

Start by looking at the basic batcher script `batchSubjects.py` to apply CTP on many subjects.

Then the `AsTRALSubjectBatcher.py` has more advanced code which enables dynamically rewriting the CTP script and launching the CTP java web service locally so that each subject can have a different random date offset.

## Removing potentially identifiable DICOMs

After running CTP, you may still need to delete some files that may have burn-in patient data, such as dose reports, or visible face, 
such as T1w MPRAGEs. you can use `delete_identifiable_DICOMs.py`. The conda environfment in `envs/env_dev.yml` will install the required dependencies.
