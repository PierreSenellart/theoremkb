import os
import re
import pandas as pd
import numpy as np

PATH_SRC = "../DATA/CC-src/"
PATH_JSON = "../DATA/CC-json/"
PATH_PDF = "../DATA/CC-pdf/"

PAPERS = "../DATA/graph-references/graph-3/papers.csv"
REFERENCES = "../DATA/graph-references/graph-3/references.csv"
CITATIONS = "../DATA/graph-references/graph-3/cite_thm.csv"
LIST_THM = ["theorem","lemma","thm","lem","corollary","proposition","prop"]


RE_CITING = r'[a-z]*cite[a-z]*\{([\w]*)\}'
RE_HEADER = r'begin{(theorem|lemma|thm|lem|corollary|proposition|prop)}\[([^\]]+)\]'

DATASET_THM = "dataset_thm.csv"


# Dictionary (source, bibitem) -> reference

class paperGraph(object):
	def __init__(self,paper_path,ref_path):
		self.dico = {}
		df_paper = pd.read_csv(paper_path,dtype=str)
		for _,row in df_paper.iterrows():
			self.dico[row['filename']] = {}

		df_ref = pd.read_csv(ref_path,dtype=str)
		for _,row in df_ref.iterrows():
			if row['bibitem'] != None:
				self.dico[row['pdf_from']][row['bibitem']] = row['pdf_to']


	def getitem(self,pdf_from,bibitem):
		if pdf_from not in self.dico.keys():
			return None
		if bibitem not in self.dico[pdf_from].keys():
			return None
		return self.dico[pdf_from][bibitem]


# Dictionary (paper) -> LIST (paper source, theoreme data)
class paperThm(object):
	def __init__(self):
		self.dico = {}

	def additem(self,target,thm,src,head):
		if target not in self.dico.keys():
			self.dico[target] = []
		self.dico[target].append((src,thm,head))

	def getkeys(self):
		return self.dico.keys()

	def getlist(self,key):
		return self.dico[key]
		
		

# Clean a theorem
def clean_thm(thm):
	thm_clean = str(thm).lower()
	thm_clean = re.sub(r'\\[a-z]*(begin|end|cite|label|footnote|ref)[a-z]*\{[\w\s,\*:-]+\}(\[[^\]]+\])?',' ',thm_clean)
	thm_clean = re.sub(r'([\+\*\^<>=_-])',r' \1 ',thm_clean)
	thm_clean = re.sub(r'([0-9]+)',r' \1 ',thm_clean)
	thm_clean = re.sub(r'[^a-z0-9<>=\+\*\^_-]+'," ",thm_clean)
	return thm_clean


# Get references from panda file into an array
def get_paper(path_citation):
	citations = pd.read_csv(path_citation,dtype=str)
	count_kind = {
			"theorem":0,
			"lemma":0,
			"corollary":0}

	count_kind_intra = {
			"theorem":0,
			"lemma":0,
			"corollary":0}

	look_at = []
	for _,row in citations.iterrows():
		if row.thm_kind in ["thm","theorem"]:
			count_kind["theorem"] += 1
			if not(pd.isnull(row.paper_to)):
				if row.paper_from not in look_at:
					look_at.append(row.paper_from)
				count_kind_intra["theorem"] += 1
		elif row.thm_kind in ["lem","lemma"]:
			count_kind["lemma"] += 1
			if not(pd.isnull(row.paper_to)):
				if row.paper_from not in look_at:
					look_at.append(row.paper_from)
				count_kind_intra["lemma"] += 1
		else:
			count_kind["corollary"] += 1
			if not(pd.isnull(row.paper_to)):
				if row.paper_from not in look_at:
					look_at.append(row.paper_from)
				count_kind_intra["corollary"] +=1



	print("Total : ",count_kind)
	print("Intra-corpus : ",count_kind_intra)

	return look_at
	





# Find thm in a file with another paper cited inside

def find_all_thm(dataset,filename,pg):
	data_thm = dataset[dataset.src == filename]
	ref_out = []
	for index,row in data_thm.iterrows():
		thm = row.theorem
		ref_list = re.findall(RE_CITING,thm,re.IGNORECASE)
		for ref in ref_list:
			target = pg.getitem(filename,ref)
			if target == None:
				continue
				
			header_v = re.findall(RE_HEADER,thm,re.IGNORECASE)
			if len(header_v) == 0:
				head = None
			else:
				head = header_v[0]
			
			thm_clean = clean_thm(thm)
			ref_out.append((target,filename,thm_clean,head))
	return ref_out
	
	
# Get all theorems from one paper
	
def search_thm(dataset,filename):
	txt_list = []
	data_thm = dataset[dataset.src==filename]
	for index,row in data_thm.iterrows():
		thm = row.theorem
		txt_list.append(clean_thm(thm))
	return txt_list
		
	



# Iterate the function find_all_thm over all papers of the corpus

def find_thm_from(dataset,look_at,verbose=False,papers_path=PAPERS,ref_path=REFERENCES):
	out_doc = []
	pg = paperGraph(papers_path,ref_path)
	pt = paperThm()
	for paper in look_at:
		if verbose:
			print(paper)
		out = find_all_thm(dataset,paper,pg)
		if out == None:
			continue
		for (tgt,src,thm,head) in out:
			pt.additem(tgt,thm,src,head)
	return pt
	
	
	
def find_all_matches(dataset,tgt):
	return search_thm(dataset,tgt)



# Save an array of matched thm as csv file

def matchs_to_csv(match_array,title,path_out="",extra=[]):
	path_out = path_out+"matching_thm_%s.csv"
	df = pd.DataFrame(match_array)
	df.to_csv(path_out%title,index=False,
			header=['confidence','source','target','thm_source','thm_target']+extra)


