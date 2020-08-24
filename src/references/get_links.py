import json
import os
import pandas as pd
import requests
import xml.etree.ElementTree as ETree
import re
from TexSoup import TexSoup


from ..config import SOURCE_PATH, STUFF_PATH, GRAPH_PATH

path_links = STUFF_PATH + "/links.csv"


grobid_url = 'http://localhost:8070/api/'
grobid_references = grobid_url + 'processReferences'
grobid_document = grobid_url + 'processFulltextDocument'
teipath = "{http://www.tei-c.org/ns/1.0}"

# convert a pdf into a xml with grobid

def pdf2xml(pdf_path,kind='references'):
	if kind == 'references':
		url = grobid_references
	elif kind == 'fulltext':
		url = grobid_document
	files= {
		'input': (
			pdf_path,
			open(pdf_path,'rb'),
			'application/pdf',
			{'Expires':'0'}
		)
	}
	
	out = requests.request(
		"POST",
		url,
		headers={'Accept':'application/xml'},
		params={},
		files=files,
		data={},
		timeout=None,
	)

	if out.status_code == 200:
		root = ETree.fromstring(out.text)
		return (200,root)
	else:
		return (out.status_code,None)



# Go through all references on the tei.xml and compare title with title
# of other references to find the grobid number of each reference

def getitem(pdf_path,title_list,dict_output):
	(out_code,xmlTree) = pdf2xml(pdf_path,'fulltext')
	title_numb = {}
	idx2idf = {}
	title_list_copy = title_list[::]
	if out_code != 200:
		for title,ref in title_list_copy:
			title_numb[ref] = -1
			dict_output["GROBID_ERR"] += 1
		return title_numb,idx2idf
	
	n_item = 0
	for item in xmlTree.iter(teipath+'biblStruct'):
		id_v = '{http://www.w3.org/XML/1998/namespace}id'
		if id_v not in item.attrib:
			continue
		title = ""
		for title_el in item.iter(teipath+"title"):
			if "type" in title_el.attrib and title_el.attrib["type"] == "main":
				title = title_el.text.lower()
				title = re.sub(r'[^a-z]','',title)
				break
		
		for i in range(len(title_list_copy)):
			if title_list_copy[i][0] == title:
				title_numb[title_list_copy[i][1]] = n_item
				title_list_copy.pop(i)
				break
		n_item += 1
	
	for ref in xmlTree.iter(teipath+"ref"):
		if "type" not in ref.attrib or ref.attrib["type"] != "bibr":
			continue
		if "target" not in ref.attrib:
			continue
		tgt = int(ref.attrib["target"][2:])
		if tgt not in idx2idf:
			idx2idf[tgt] = []
		txt = re.sub(r'\W','',ref.text)
		idx2idf[tgt].append(txt)
	
	for title,ref in title_list_copy:
		dict_output['TNF'] += 1
		title_numb[ref] = -1
	
	return title_numb,idx2idf


def get_links(subdirectory=""):
	
	path_pdf = SOURCE_PATH +"/"+ subdirectory + "/pdf"
	df_links = pd.read_csv(path_links,dtype=str)
	dict_output = {"DFN":0,"BNF":0,"TNF":0,"2SRCNF":0,"2REFNF":0,"2BBLNF":0,"2UNREAD_BBL":0,"GROBID_ERR":0,"NOTAGS":0,"SUCCESS":0}
	list_pairs = {}
	alldir = list(os.listdir(path_pdf))
	ndir = len(alldir)
	df_list = []
	i = 0
	for f in alldir:
		if i > 0 and i%100 == 0:
			print("%i/%i"%(i,ndir))
		i +=1

		fname = f[:-4]
		title_list = []
		fname_df = re.sub(r'([a-z])(\d)',r'\1/\2',fname)
		df_f = df_links[df_links.pdf_from == fname_df]
		for _,row in df_f.iterrows():
				title = row['title'].lower()
				title = re.sub(r'[^a-z]','',title)
				arxivId = row['pdf_to']
				title_list.append((title,arxivId))

		# check for titles in references
		refpos = {}
		if title_list != []:
			refpos,idx2idf = getitem(path_pdf +"/"+ f,title_list,dict_output)
		
		else:
			dict_output["DFN"] += 1
		tags_2 = []
		grobid_index = []
		for _,row in df_f.iterrows():
			arxivId = row['pdf_to']
			if arxivId in refpos:
				pos = refpos[arxivId]
				grobid_index.append(pos)
				if pos in idx2idf:
					dict_output["SUCCESS"] += 1
					tags_2.append("-".join(list(set(idx2idf[pos]))))
				else:
					dict_output["NOTAGS"] += 1
					tags_2.append(None)
			else:
				dict_output["BNF"] += 1
				grobid_index.append(-2)
				tags_2.append(None)

		df_f["grobid_index"] = grobid_index
		df_f["tags_2"] = tags_2	
		df_list.append(df_f)
	
	print(dict_output)
	data = pd.concat(df_list)	
	data.to_csv("%s/links_%s.csv"%(GRAPH_PATH,subdirectory),
				index=False)

