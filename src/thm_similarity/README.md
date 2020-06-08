# Given a theorem with a references to another paper inside it, we want to be able to find the precise theorem which is used by using only similiarities between sentences.

## Tools : 
* create_dataset_thm : Script to extract all theorems from papers in the corpus
* thmtools : Some functions to use the theorems dataset
* glovetools : Functions for glove embeddings

## Models :
* model_tfidf : Simple but efficient model using a TFIDF Vectorizer (~ 80% success)
* train_autoencoder and model_autoencoder : An autoencoder model in order to create sentence emebddings for theorems using Glove embeddings. This use the work from https://arxiv.org/abs/1511.06349 (bad success rate so far ~ 50% success)

