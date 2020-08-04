import os
import re
import xml.etree.ElementTree as ETree
import pandas as pd


from ..config import STUFF_PATH, SRC_PATH
from .get_links import pdf2xml, teipath

PAPER_GRAPH_PATH = STUFF_PATH + "/references_grobid_index.csv"
path_pdf = SRC_PATH + "/src/"

def extract_refs(filepath):
	df = pd.read_csv(filepath,dtype=str)
	dico_pdf = {}
	for _,row in df.iterrows():
		pdfname = row.pdf_from
		gindex = row.grobid_index
		if gindex == '-1':
			continue
		if pdfname not in dico_pdf.keys():
			dico_pdf[pdfname] = {}
		dico_pdf[pdfname][gindex] = row.pdf_to

	return len(df),dico_pdf



def find_tag():
	
	# Extract all links from previous step
	nb_ref,dico_grobid = extract_refs(PAPER_GRAPH_PATH)

	c_seen = 0
	c_notseen = 0

	df_out = []
	for f in os.listdir(XML_PATH):
		c_seen_i  = 0

		fname = f[:-4]

		if fname not in dico_grobid.keys():
			continue

		try:
			idx2idf = {}
			(out_code,tree) = pdf2xml(pdf_path,'fulltext')
			if out_code != 200:
				print("Grobid failed")
				continue
			# Check all references that are bibr ref and have a target
			for ref in tree.iter(teipath+"ref"):
				if "type" not in ref.attrib or ref.attrib["type"] != "bibr":
					continue
				if "target" not in ref.attrib:
					continue

				tgt = ref.attrib["target"][2:]
				if tgt not in idx2idf:
					idx2idf[tgt] = []

				# Associate the tag to the grobid index
				txt = re.sub(r'\W','',ref.text)
				idx2idf[tgt].append(txt)

			# Save tag that are interesting for us
			for id in idx2idf:
				tgt = None
				l = list(set(idx2idf[id]))
				if id in dico_grobid[fname].keys():
					c_seen_i += 1
					tgt = dico_grobid[fname][id]
				for new_id in l:
					df_out.append((fname,new_id,tgt))

			c_notseen += len(dico_grobid[fname].keys())-c_seen_i
			c_seen += c_seen_i

		except:
			print("Parsing Error")	

	print("%i paper seen"%i)
	print("%i/%i in grobid"%(c_seen+c_notseen,nb_ref))
	print("%i/%i found"%(c_seen,c_seen+c_notseen))

	df_out = pd.DataFrame(df_out)
	df_out.to_csv(STUFF_PATH+"/references_tag.csv",index=False,header=["source","identifiant","target"])

