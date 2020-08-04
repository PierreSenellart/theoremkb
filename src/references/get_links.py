import json
import os
import pandas as pd
import requests
import xml.etree.ElementTree as ETree
import re
from TexSoup import TexSoup


from ..config import SRC_PATH, STUFF_PATH

path_pdf = SRC_PATH + "/src/"

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
	(out_code,xmlTree) = pdf2xml(pdf_path,'references')
	title_numb = []

	title_list_copy = title_list[::]
	if out_code != 200:
		for title,ref in title_list_copy:
			title_numb.append((ref,-1))
			dict_output["GROBID_ERR"] += 1
		return title_numb
	
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
				title_numb.append((title_list_copy[i][1],n_item))
				title_list_copy.pop(i)
				break
		n_item += 1
	
	
	for title,ref in title_list_copy:
		dict_output['TNF'] += 1
		title_numb.append((ref,-1))
	
	return title_numb


def get_refs():

	dict_output = {"TNF":0,"2SRCNF":0,"2REFNF":0,"2BBLNF":0,"2UNREAD_BBL":0,"GROBID_ERR":0}
	list_pairs = {}

	for f in os.listdir(path_json):

		# open the json file
		full_path = path_json + "/" + f

		file_name = f[:-5]

		data = json.load(open(full_path))
		references = data['references']

		title_list = []

		# save all the links to other arxiv papers
		for ref in references:
			arxivId = ref['arxivId']
			if arxivId != None:
				arxivId = re.sub('/','',arxivId)
				
				# get infos
				intents = ref['intent']
				methodology = 'methodology' in intents
				result = 'result' in intents
				background = 'background' in intents
				influential = ref['isInfluential']
				
				# get title
				title = ref['title'].lower()
				title = re.sub(r'[^a-z]','',title)
				title_list.append((title,arxivId))

				# add pair
				list_pairs[(file_name,arxivId)] = {
					'influential':influential,
					'background':background,
					'result':result,
					'methodology':methodology
					}
		
		# check for titles in references
		if title_list != []:
			refpos = getitem(path_pdf + file_name + ".pdf",title_list,dict_output)
			for (ref,pos) in refpos:
				list_pairs[(file_name,ref)]['grobid_index'] = pos
				list_pairs[(file_name,ref)]['bibitem'] = None
		
	pairs = []
	for k in list_pairs.keys():
		v = list_pairs[k]
		pairs.append([k[0],
					k[1],
					v['influential'],
					v['background'],
					v['result'],
					v['methodology'],
					v['grobid_index']]
					)

	# save it
	data = pd.DataFrame(pairs)
	data.to_csv(STUFF_PATH + '/references_grobid_index.csv',
				index=False,
				header=['pdf_from','pdf_to','influential','background','result','methodology','grobid_index'])

