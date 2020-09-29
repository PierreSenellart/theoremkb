import numpy as np
import pandas as pd
import torch
from annoy import AnnoyIndex


# Create vocabulary from Glove File


class GloveEmbeddings(object):

    def __init__(self,EMB_SIZE=50,PATH_EMB=None):
        if not(PATH_EMB):
            GLOVE_EMBEDDINGS = "../DATA/embeddings/glove.6B.%id.txt"%EMB_SIZE
        else:
            GLOVE_EMBEDDINGS = PATH_EMB
        self.embeddings = []
        self.word_to_index = {}
        self.index_to_word = []
        self.Aindex = AnnoyIndex(EMB_SIZE,metric='euclidean')

        with open(GLOVE_EMBEDDINGS,"r") as fp:
            for index, line in enumerate(fp):
                line = line.split()
                self.word_to_index[line[0]] = index
                self.index_to_word.append(line[0])
                embedding_i = np.array([float(val) for val in line[1:]])
                self.embeddings.append(embedding_i)
                self.Aindex.add_item(index,embedding_i)

        self.Aindex.build(50)
        self.embedding_dim = EMB_SIZE
        self.unknown = torch.rand(EMB_SIZE)

    # Check if a word is in the vocab
    def is_in_glove(self,word):
        return (word in self.word_to_index.keys())
        
    # Get embeddings for a world
    def emb(self,word,tensor=True):
        if word not in self.word_to_index.keys():
            return None
        embd = self.embeddings[self.word_to_index[word]]
        if tensor:
            embd = torch.Tensor(embd)
        return embd

    # Get embeddings from a text
    def embtxt(self,text,tensor=True):
        text = text.split()
        embeddings = []
        for word in text:
            emb_i = self.emb(word,tensor)
            if emb_i == None:
                embeddings.append(self.unknown)
            else:
                embeddings.append(emb_i)
        
        if embeddings == []:
            return 0,[]
        embeddings = torch.stack(embeddings)
        return len(text),embeddings

    # Get the closest neighbor of an embeddings
    def get_closest_neighbor(self,vector,n=1):
        nn_indices = self.Aindex.get_nns_by_vector(vector,n)
        return [self.index_to_word[neighbor] for neighbor in nn_indices]

    # Get a text from embeddings using the above function.
    def emb_to_txt(self,embs):
        (seq_len,_) = embs.size()
        s = ""
        for i in range(seq_len):
            word = self.get_closest_neighbor(embs[i])[0]
            if i > 0:
                s += " "
            s += word
        return s
