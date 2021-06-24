import os
import re
import numpy as np
import pandas as pd
from TexSoup import TexSoup


PATH_SRC = "../DATA/CC-src/"
LIST_THM = ["theorem","lemma","thm","lem","corollary","proposition","prop"]


def search_thm(filepath,clean=True):
	try:
		txt_list = []
		soup = TexSoup(open(filepath,'r'))
		for kind in LIST_THM :
			gen = soup.find_all(kind)
			thm_list = list(gen)
			for thm in thm_list:
				if clean:
					thm_clean = clean_thm(thm)
				else:
					thm_clean = str(thm)
				txt_list.append(thm_clean)
		return txt_list
		
	except UnicodeDecodeError as error:
		return []
	except EOFError as error:
		return []
	except TypeError as error:
		return []

def find_all_matches(tgt,clean=True):
	thm_list = []
	pathfile = PATH_SRC + tgt.replace(".","-")
	if not (os.path.isdir(pathfile)):
		return []
	qpath = [pathfile]
	while qpath != []:
		curr_path = qpath.pop(0)
		for f in os.listdir(curr_path):
			newpath = curr_path + "/" + f
			
			if os.path.isdir(newpath):
				qpath.append(newpath)
				continue

			ext = f.split(".")[-1]
			if ext == "tex":
				thm_list.extend(search_thm(newpath,clean=clean))
				
	return thm_list
	
	

def savefile(thm_dataset):
	df = pd.DataFrame(thm_dataset)
	df.to_csv("dataset_thm.csv",index=False,header=["src","theorem"])	
	
	
def main():
	thm_dataset = []
	total = 0
	for f in os.listdir(PATH_SRC):
		
		
		if i%100 == 99:
			print("SAVING (%i)"%(i+1))
			savefile(thm_dataset)
	
		filename = f.split('.')[0].replace("-",".")
		new_data = find_all_matches(filename,clean=False)
		total += len(new_data)
		print("%s : %i (total : %i)"%(filename,len(new_data),total))
		for thm in new_data:
			thm_dataset.append((filename,thm))

	savefile(thm_dataset)
	


main()
