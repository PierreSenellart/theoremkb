from sklearn.feature_extraction.text import TfidfVectorizer
import thmtools as tools
import numpy as np
import pandas as pd
import re

def tfidf(save=False,verbose=True):
    look_at = tools.get_paper("cite_thm.csv")
    
    dataset = pd.read_csv("dataset_thm.csv",dtype=str)

    pt = tools.find_thm_from(dataset,look_at,verbose=False,
                            papers_path='papers.csv',ref_path='references.csv')
    
    out_doc = []
    keys = pt.getkeys()
    c = 0
    for tgt in keys:
        thm_list = tools.find_all_matches(dataset,tgt)
        n_tgt= len(thm_list)
        
        vect = TfidfVectorizer(stop_words="english")
        
        file_list = [p[0] for p in pt.getlist(tgt)]
        src_list = [p[1] for p in pt.getlist(tgt)]
        head_list = [p[2] for p in pt.getlist(tgt)]
        
        thm_list.extend(src_list)
        tfidf = vect.fit_transform(thm_list)
        pairwise_similarity = tfidf * tfidf.T
        pairwise_similarity = pairwise_similarity.toarray()
        matrix = pairwise_similarity[:n_tgt,n_tgt:].T
        
        if len(matrix[0]) == 0:
            continue
        if verbose:
          print(('*'*50+'\n')*3)
        for i in range(len(matrix)):

            '''
            if head_list[i] == None or head_list[i][1] == None:
                continue
            head = head_list[i][1].lower()
            if head.find("theorem") < 0 and head.find("lemma") < 0 and head.find("collorary") < 0:
                continue
            '''
            
            row = matrix[i]
            maxi = np.argmax(row)
            maxv = np.max(row)
            if verbose:
              print("%s -> %s"%(file_list[i],tgt))
            c += 1
            if verbose:
              print("*"*70)
            if head_list[i] != None and verbose:
                print("HEADER : ",head_list[i])
            if verbose:
              print("SOURCE : ",src_list[i])
              print("TARGET : ",thm_list[maxi])
              print("Confidence : ",maxv)

           

            out_doc.append((maxv,file_list[i],tgt,src_list[i],thm_list[maxi],head_list[i][1].lower()))
            
    out_doc.sort()
    out_doc.reverse()
    print("%i theorems matched"%c)
    
    if save:
        tools.matchs_to_csv(out_doc,"tfidf_only",extra=["header"])
    
    
    
