import os, sys

HOME           = os.getenv("HOME")
USER           = os.getenv("USER")

if USER == "lpluvina":
    base = f"{HOME}/theoremkb"
elif USER == "lucas":
    base = f"{HOME}/stage"
else:
    print("config/__init__.py: error: set-up your user here.", file=sys.stderr)
    exit(1)

# databases/datasets
DATA_PATH      = f"{base}/exthm-data/data"