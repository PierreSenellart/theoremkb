import os 

FEATURE_MODE   = "word" # line | word -based

HOME           = os.getenv("HOME")

# raw article and sources, located in CC-src and CC-pdf.
SOURCE_PATH    = f"{HOME}/stage/DATA"
# extracted sources: they have the latex extraction module inserted.
WORKING_PATH   = f"{HOME}/stage/exthm-data/extracted_sources"
# extracted pdf + xml files.
TARGET_PATH    = f"{HOME}/stage/exthm-data/extracted_data"
# databases/datasets
DATA_PATH      = f"{HOME}/stage/exthm-data/data"

def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
