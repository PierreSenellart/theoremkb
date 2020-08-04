import os,re
import requests
import pandas as pd
import time
import json

from ..config import JSON_PATH, SOURCE_PATH


path_pdf = SOURCE_PATH + "/src"
api_semanticscholar = "https://api.semanticscholar.org/v1/paper/arXiv:"


def download_json(sleep_time=2):
	already_seen =[]

	# Check all the json already downloaded
	for f in os.listdir(JSON_PATH):
		already_seen.append(f[:-5])
		
	c,c_ok = 0,0
	dico_code = {}

	for f in os.listdir(path_pdf):
		if c > 0 and c%100 == 0:
			print("%i/%i files downloaded"%(c_ok,c))

		c += 1
		
		# We get the arxivId of the paper
		name = f[:-4]
		arxivId = re.sub(r'([a-z])(\d)',r'\1/\2',name)

		# We check if it is not already downloaded
		if name in already_seen:
			continue

		# We send ou request to semanticscholar
		url = api_semanticscholar + arxivId
		time.sleep(sleep_time)
		response = requests.get(url)

		# get status_code
		if response.status_code not in dico_code.keys():
			dico_code[response.status_code] = 0
		dico_code[response.status_code] += 1

		# save the json file
		if response.status_code == 200:
			c_ok += 1
			json_content = response.json()
			file_path = JSON_PATH + "/" + name + ".json"
			with open(file_path,'w') as json_file:
				json.dump(json_content,json_file)

	print(dico_code)
