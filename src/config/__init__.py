import os , sys

FEATURE_MODE   = "word" # line | word -based

REGENERATE     = True

HOME           = os.getenv("HOME")
USER           = os.getenv("USER")

if USER == "lpluvina":
    base = f"{HOME}/theoremkb"
elif USER == "lucas":
    base = f"{HOME}/stage"
elif USER == "tdelemazure":
    base = f"{HOME}/theoremkb"
else:
    print("config/__init__.py: error: set-up your user here.", file=sys.stderr)
    exit(1)

# raw article and sources, located in CC-src and CC-pdf.
SOURCE_PATH    = f"{base}/aws-data/selection"
# extracted sources: they have the latex extraction module inserted.
WORKING_PATH   = f"{base}/exthm-data/extracted_sources"
# extracted pdf + xml files.
TARGET_PATH    = f"{base}/exthm-data/extracted_data"
# databases/datasets
DATA_PATH      = f"{base}/exthm-data/data"
# logs
LOGS_PATH      = f"{base}/exthm-data/logs"
# links
LINKS_PATH     = f"{base}/DATA/links"

def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

LIST_RESULTS = ["theorem",
				"claim",
				"case",
				"conjecture",
				"corollary",
				"definition",
				"lemma",
				"example",
				"exercice",
				"lemma",
				"note",
				"problem",
				"property",
				"proposition",
				"question",
				"solution",
				"remark",
				"fact",
				"hypothesis",
				"observation"]