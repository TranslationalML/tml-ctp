# Depersonalisation tools

Tools, whilelists, blacklists, configuration files for depersonalising imaging data.

## Getting started

The RSNA MIRC Clinical Trial Processor (CTP) DICOM anonymiser is the core engine. CTP doc is here: <https://mircwiki.rsna.org/index.php?title=MIRC_CTP> and the doc for the syntax for the anonymiser script is here: <https://mircwiki.rsna.org/index.php?title=The_CTP_DICOM_Anonymizer>.

Start by looking at the basic batcher script `batchSubjects.py` to apply CTP on many subjects.

Then the `AsTRALSubjectBatcher.py` has more advanced code which enables dynamically rewriting the CTP script and launching the CTP java web service locally so that each subject can have a different random date offset.
