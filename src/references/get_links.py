import json
import os
import pandas as pd
import requests
import xml.etree.ElementTree as ETree
import re
from TexSoup import TexSoup


from ..config import SRC_PATH, STUFF_PATH, GRAPH_PATH

path_pdf = SRC_PATH + "/pdf/"
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
			title_numb.append[ref] = -1
			dict_output["GROBID_ERR"] += 1
		return title_numb,idx2idf
	
	n_item = 0
	for item in xmlTree.iter(teipath+'biblStruct'):
		for title_el in item.iter(teipath+"title"):
			title = ""
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
	
	for ref in tree.iter(teipath+"ref"):
		if "type" not in ref.attrib or ref.attrib["type"] != "bibr":
			continue
		if "target" not in ref.attrib:
			continue
		tgt = ref.attrib["target"][2:]
		if tgt not in idx2idf:
			idx2idf[tgt] = []
		txt = re.sub(r'\W','',ref.text)
		idx2idf[tgt].append(txt)
	
	for title,ref in title_list_copy:
		dict_output['TNF'] += 1
		title_numb[ref] = -1
	
	return title_numb,idx2idf


def get_refs(subdirectory=""):
	
	path_pdf += subdirectory + "/"
	df_links = pd.read_csv(path_links,dtype=str)
	dict_output = {"BNF":0,"TNF":0,"2SRCNF":0,"2REFNF":0,"2BBLNF":0,"2UNREAD_BBL":0,"GROBID_ERR":0}
	list_pairs = {}

	df_list = []
	for f in os.listdir(path_pdf):
		fname = f[:-4]
		title_list = []
		df_f = df_links[df_links.pdf_from == fname]
		for _,row in df_f.iterrows():
				title = row['title'].lower()
				title = re.sub(r'[^a-z]','',title)
				arxivId = row['pdf_to']
				title_list.append((title,arxivId))

		# check for titles in references
		refpos = {}
		if title_list != []:
			refpos,idx2idf = getitem(path_pdf + file_name + ".pdf",title_list,dict_output)

		for _,row in df_f.iterrows():
			arxivId = row['pdf_to']
			if arxivId in refpos:
				row['grobid_index'] = pos
				if pos in idx2idf:
					row['tags_2'] = "-".join(idx2idf[pos])
				else:
					row['tags_2'] = None
			else:
				dict_output["BNF"] += 1
				row['grobid_index'] = -2
				row['tags_2'] = None

		
		df_list.append(df_f)
	

	data = pd.concat(df_list)	
	data.to_csv("%s/links_%s.csv"%(GRAPH_PATH,subdirectory),
				index=False)

