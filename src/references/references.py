from .download_json import download_json
from .get_links import get_refs
from .get_tags import find_tag
import time
import pandas as pd


def build_dico():
	print("STEP 1 : DOWNLOAD JSON")
	t0 = time.time()
	download_json()
	t1 = time.time()
	print("STEP 2 : FIND LINKS")
	get_refs()
	t2 = time.time()
	print("STEP 3 : FIND TAGS")
	find_tag()
	t3 = time.time()
	t = (t1-t0,t2-t1,t3-t2)
	print("Step 1 : %.2f \n Step 2 : %.2f \n Step 3 : %.2f"%t)


def load_dico():
	df = pd.read_csv(PATH,index_col=0,dype=str)
	()#todo


def use_dico():
	()#todo
