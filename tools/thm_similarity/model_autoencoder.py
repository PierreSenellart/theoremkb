import pandas as pd
import torch
import thmtools as tools

def autoencoder_thm(save=False,verbose=True,metric="cosine",model_path="autoencoder.nn"):

    model = torch.load(model_path)

    look_at = tools.get_paper("cite_thm.csv")
    dataset = pd.read_csv("dataset_thm.csv",dtype=str)

    pt = tools.find_thm_from(dataset,look_at,verbose=False,
                            papers_path='papers.csv',ref_path='references.csv')
    
    out_doc = []
    keys = pt.getkeys()
    
    if metric == "cosine":
      sim = nn.CosineSimilarity(dim=1,eps=1e-6)
    elif metric == "euclid":
      sim = nn.PairwiseDistance(p=2.0, eps=1e-06)
    c = 0
    for tgt in keys:
        thm_list = tools.find_all_matches(dataset,tgt)
        n_tgt= len(thm_list)
        if len(thm_list) == 0:
            continue
        
        tgt_features = []
        for tgt_thm in thm_list:
          if tgt_thm.strip() == "":
            continue
          else:
            tgt_features.append(get_features(vocab,tgt_thm,model))
        tgt_features = torch.stack(tgt_features)
        
        file_list = [p[0] for p in pt.getlist(tgt)]
        src_list = [p[1] for p in pt.getlist(tgt)]
        head_list = [p[2] for p in pt.getlist(tgt)]
        src_features = [get_features(vocab,src_thm,model) for src_thm in src_list]
        
        
        if verbose:
          print(('*'*50+'\n')*3)
        for i in range(len(src_list)):

            '''
            if only:
                if head_list[i] == None or head_list[i][1] == None:
                  continue
                head = head_list[i][1].lower()
                if head.find("theorem") < 0 and head.find("lemma") < 0 and head.find("collorary") < 0:
                  continue
                  
            '''
            
            src_f = torch.Tensor(src_features[i]).unsqueeze(0)
            
            similarity = sim(src_f,tgt_features)

            if metric == 'euclid':
              similarity = -similarity
            max_similarity = torch.max(similarity).item()
            argmax_similarity = torch.argmax(similarity).item()
            if verbose:
              print("%s -> %s"%(file_list[i],tgt))
            c += 1
            if verbose:
              print("*"*70)
            if head_list[i] != None and verbose:
                print("HEADER : ",head_list[i])
            if verbose:
              print("SOURCE : ",src_list[i])
              print("TARGET : ",thm_list[argmax_similarity])
              print("Confidence : ",max_similarity)


            out_doc.append((max_similarity,file_list[i],tgt,src_list[i],thm_list[argmax_similarity],head_list[i][1].lower()))
            
    out_doc.sort()
    out_doc.reverse()
    print("%i theorems matched"%c)
    
    if save:
        tools.matchs_to_csv(out_doc,"autoencod",extra=["header","success"])