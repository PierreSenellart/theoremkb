import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
import copy

import thmtools as tools
import glovetools as glove

EMB_SIZE = 50
FEATURES_DIM = 100
HIDDEN_DIM = 100
N_LAYERS = 1
WORD_DROPOUT = 0.5
N_EPOCHS = 20
BATCH_SIZE = 64
BIDIRECTIONAL = TRUE
DATASET_THM = "dataset_thm.csv"
MAX_THM = 1000



def to_var(x, volatile=False):
    #if torch.cuda.is_available():
    #    x = x.cuda()
    return Variable(x, volatile=volatile)
    

# Encoder : Theorem -> Features
class Encoder(nn.Module):

    def __init__(self,embeddings_dim,hidden_size,
                features_dim,num_layers=1,bidirectional=True):
        
        super(Encoder, self).__init__()
        '''
        self.emb = nn.Embedding(embedding_dim=embeddings_dim,
                                num_embedding=vocab_size,
                                padding_idx=0,
                                _weight=embeddings)
        '''	

        self.rnn = nn.GRU(input_size=embeddings_dim,
                            hidden_size=hidden_size,
                            num_layers =num_layers,
                            batch_first=True,
                            bidirectional=bidirectional)

        self.features_dim = features_dim
        self.hidden_factor = (2 if bidirectional else 1) * num_layers
        self.hidden2mean = nn.Linear(hidden_size * self.hidden_factor, features_dim)
        self.hidden2logv = nn.Linear(hidden_size * self.hidden_factor, features_dim)

    def forward(self,x,add_rand=True):
        
        #x = self.emb(x)
        x = x.unsqueeze(0)

        _, hidden_n = self.rnn(x)
        hidden_n = hidden_n.view(-1)

        mean = self.hidden2mean(hidden_n)
    
        if add_rand:
            logv = self.hidden2logv(hidden_n)
            std = torch.exp(0.1 * logv)
    
            z = to_var(torch.randn( self.features_dim))
            z = z * std + mean
        else:
            z = mean

        return z
    

# Decoder : Features + Partial Theorem (ex : 50% of words) -> Theorem
class Decoder(nn.Module):

    def __init__(self,embeddings_dim,features_dim,
                hidden_dim,unk_emb,num_layers=1,bidirectional=True,
                word_dropout_rate=0.5):

        super(Decoder,self).__init__()
        if bidirectional:
            factor = 2
        else:
            factor = 1

        self.hidden_factor = (2 if bidirectional else 1) * num_layers

        self.rnn = nn.GRU(input_size=embeddings_dim,
                            hidden_size=hidden_dim,
                            num_layers =num_layers,
                            batch_first=True,
                            bidirectional=bidirectional)
    
        self.word_dropout_rate = word_dropout_rate
        self.bidirectional = bidirectional
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim
        self.factor = factor
        self.unk_emb = unk_emb

        self.latent2hidden = nn.Linear(features_dim, hidden_dim * self.hidden_factor)
        self.outputs2vocab = nn.Linear(hidden_dim * (2 if bidirectional else 1), embeddings_dim)

    def forward(self,x,z):

        hidden = self.latent2hidden(z)
        hidden = hidden.view(self.hidden_factor,1,self.hidden_dim)

        seq_length,emb_dim = x.size()

        if self.word_dropout_rate > 0:
      # randomly replace decoder input with <unk>
            prob = torch.rand(seq_length)
            if torch.cuda.is_available():
                prob=prob.cuda()

            decoder_input_sequence = x.clone()
            decoder_input_sequence[prob < self.word_dropout_rate] = self.unk_emb

        x = decoder_input_sequence.unsqueeze(0)
        x, _ = self.rnn(x,hidden)
        x = x.reshape((seq_length,self.hidden_dim*self.factor))
        out_features = self.outputs2vocab(x)
        
        return out_features
    

class AutoEncoder(nn.Module):

    def __init__(self,embeddings_dim,features_dim,
                hidden_dim,unk_emb,num_layers=1,bidirectional=True,
                word_dropout_rate=0.5):
        super(AutoEncoder,self).__init__()
    
        self.encoder = Encoder(embeddings_dim,hidden_dim,
                                features_dim,num_layers,bidirectional)
        self.decoder = Decoder(embeddings_dim,features_dim,
                                hidden_dim,unk_emb,
                                num_layers,bidirectional,
                                word_dropout_rate)

    def forward(self,x):
        f = self.encoder(x)
        y = self.decoder(x,f)
        return y
        
        
        
        
        
def train_model(model,dataset_train, dataset_val,n_epochs,vocab,batch_size=64):
    optimizer = optim.Adam(model.parameters(),lr=2*1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer=optimizer,
                            mode='min', factor = 0.5,
                            patience=1)
    criterion = nn.MSELoss()
    history = dict(train=[],val=[])

    best_model_wts = copy.deepcopy(model.state_dict())
    best_loss = 1000000.0
    optimizer.zero_grad()

    for epoch in range(1,n_epochs+1):
        dataset_train = dataset_train.sample(frac=1)
        model.train()
        
        count = 0
        train_loss = []
        for index,row in dataset_train.iterrows():
            count += 1
            if count > MAX_THM:
                break
            thm = row.theorem
            thm = tools.clean_thm(thm).strip()	
            if len(thm) == 0:
                continue
            txt_len,embeddings = vocab.embtxt(thm)
            #embeddings = embeddings.to("cuda")
            prediction = model(embeddings)
            loss = criterion(embeddings,prediction)
            loss.backward()

            train_loss.append(loss.item())

            if index%batch_size==63:
                #print("Epoch %i, batch %i : loss %.2f"%(epoch,index//batch_size+1,np.mean(train_loss)))
                optimizer.step()
                optimizer.zero_grad()
    
        val_loss = []
        model.eval()
        count = 0
        with torch.no_grad():
            for index,row in dataset_val.iterrows():
                count += 1
                if count > MAX_THM:
                    break
                thm = row.theorem
                thm = tools.clean_thm(thm).strip()	
                if len(thm) == 0:
                    continue
                txt_len,embeddings = vocab.embtxt(thm)
                prediction = model(embeddings)
                loss = criterion(embeddings,prediction)
                val_loss.append(loss.item())

        train_loss = np.mean(train_loss)
        val_loss = np.mean(val_loss)
        history['train'].append(train_loss)
        history['val'].append(val_loss)

        if val_loss < best_loss:
            best_loss = val_loss
            best_model_wts = copy.deepcopy(model.state_dict())
    
        print('Epoch %i : train loss (%.2f) val loss (%.2f)'%(epoch,train_loss,val_loss))
    
    model.load_state_dict(best_model_wts)
    return model.eval(),history
        
        
        
def preprocess():
    print("Loading dataset...")
    dataset_thm = pd.read_csv(DATASET_THM,dtype=str)
    
    n_thm = len(dataset_thm)
    n_train = int(n_thm*0.9)
    print(n_thm,n_train)
    dataset_train = dataset_thm[:n_train]
    dataset_val = dataset_thm[n_train:]
    
    print("Loading embeddings...")
    vocab = glove.GloveEmbeddings(PATH_EMB="glove.6B.%id.txt"%EMB_SIZE)
    
    
    return dataset_train, dataset_val,vocab

def main(dataset_train, dataset_val,vocab,load=None):

    if load != None:
        autoencoder = torch.load(load)
    else:
        autoencoder = AutoEncoder(EMB_SIZE,FEATURES_DIM,
                                    HIDDEN_DIM,vocab.unknown,N_LAYERS,
                                    BIDIRECTIONAL,WORD_DROPOUT)
        
    #autoencoder = autoencoder.to("cuda")
    autoencoder,history = train_model(autoencoder,
                                    dataset_train,dataset_val,
                                    N_EPOCHS,vocab,BATCH_SIZE)
    torch.save(autoencoder,'autoencoder.nn')
    
    return history


def plot_history(history):
    h_train = history["train"]
    h_val = history["val"]
    plt.plot(h_train,label="train")
    plt.plot(h_val,label="val")
    plt.grid()
    plt.legend()
    plt.show()


def test_model(vocab,model_path="autoencoder.nn",s = "let x > 0 and z in \mathbb{R}" ):
  model = torch.load(model_path)
  s = tools.clean_thm(s)
  lent,embs = vocab.embtxt(s)
  new_embs = model(embs)
  new_thm =  vocab.emb_to_txt(new_embs)
  print(new_thm)


def get_features(vocab,sentence,model=None,model_path="autoencoder.nn"):
  if model == None:
    model = torch.load(model_path)
  s = tools.clean_thm(sentence)
  lent,embs = vocab.embtxt(s)
  f = model.encoder(embs,False)
  return f


#dataset_train,dataset_val,vocab = preprocess()
#history = main(dataset_train,dataset_val,vocab,load="autoencoder.nn")

