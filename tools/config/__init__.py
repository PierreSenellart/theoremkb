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
SOURCE_PATH    = f"{base}/DATA"
# extracted sources: they have the latex extraction module inserted.
WORKING_PATH   = f"{base}/exthm-data/extracted_sources_unuse"
# extracted pdf + xml files.
TARGET_PATH    = f"{base}/exthm-data/extracted_data_unuse"
# databases/datasets
DATA_PATH      = f"{base}/exthm-data/data"
# Json
JSON_PATH      = f"{base}/exthm-data/json"
# logs
LOGS_PATH      = f"{base}/exthm-data/logs"
# links
LINKS_PATH     = f"{base}/DATA/links"
# other stuff
STUFF_PATH     = f"{base}/DATA/stuff"
# graph out
GRAPH_PATH     = f"{base}/graph/"

def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

EXTTHM_STRATEGY = "override-newtheorem" # "override-newtheorem" # | override-env

EXTTHM_RESULTS = [
	"lemma",
	"theorem",
	"proposition",
	"definition",
	"remark",
	"corollary",
	"claim",
	"conjecture",
	"assumption",
	"proof"
]

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
				"observation",
				"construction"]
