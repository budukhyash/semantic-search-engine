import tensorflow as tf
import tensorflow_hub as hub
import json
import time
import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import warnings
from fastapi import FastAPI,Body
from pydantic import BaseModel
from fastapi.responses import HTMLResponse	
warnings.filterwarnings('ignore')


def connect2ES():
	'''
	This function creates a connection to the elastic search instance
	we provide the appropriate host name, port number, and authentication
	details.

	'''
	print("connecting to Elastic Search...")
	es = Elasticsearch([{'host': 'localhost', 'port': '8200','use_ssl':True,'verify_certs':False}], http_auth=('admin', 'admin'))
	if es.ping():
			print('Connected to ES!')
	else:
			print('Could not connect!')
	return es
ess = connect2ES()


def keywordSearch(es, q):
	'''
	Implements the traditional keyword search using inverted index.
	Elastic search uses a TF-IDF based metric to rank the results.

	'''

	b={
			'query':{
				'match':{
					"title":q
				}
			}
		}
	res= es.search(index='questions-index',body=b)
	return res


def sentenceSimilaritybyNN(es, sent,embed):
	'''
	Implements an approximate nearest negihbours method 
	to find the k nearest vectors.
	Elastic search relies nmslib for the implementation of HNSW
	
	https://github.com/nmslib/hnswlib
	'''
	
	query_vector = tf.make_ndarray(tf.make_tensor_proto(embed([sent]))).tolist()[0]
	kb={
		  "size": 10,
		  "query": {
			"knn": {
			  "title_vector": {
				"vector": query_vector,
				"k": 10
			  }
			}
		  }
		}

	res= es.search(index='questions-index',body=kb,request_timeout=100)
	
	return res

es = connect2ES()
class Item(BaseModel):
	query:str

print("Loading USE model...")
embed = hub.load("./use4")
app = FastAPI()

@app.post("/semantic")
async def root(item:Item): 

	result=[]
	start_time = time.time()
	ok=sentenceSimilaritybyNN(es,item.query,embed)
	for i in ok['hits']['hits']:
		result.append(i['_source']['title'])

	timeTaken = time.time() - start_time
	return {"result":result,"time_taken":timeTaken}
	   
@app.post("/keywords")
async def root(item:Item): 

	result=[]
	start_time = time.time()
	ok=keywordSearch(es,item.query)
	for i in ok['hits']['hits']:
		result.append(i['_source']['title'])

	timeTaken = time.time() - start_time
	return {"result":result,"time_taken":timeTaken,"keywords":True}

@app.get("/")
async def root():
	return {"message": "Server is running.."}

