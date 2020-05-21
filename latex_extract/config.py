import os 

REGENERATE     = True

FEATURE_MODE   = "line" # line | word -based

HOME           = os.getenv("HOME")

SOURCE_PATH    = f"{HOME}/theoremkb/DATA"
WORKING_PATH   = f"{HOME}/theoremkb/exthm-data/extracted_sources"
TARGET_PATH    = f"{HOME}/theoremkb/exthm-data/extracted_data"
TRAINING_PATH  = f"{HOME}/theoremkb/exthm-data/training_data"

def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
