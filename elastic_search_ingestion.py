import pandas as pd
import tensorflow as tf
import tensorflow_hub as hub
import json
import time
import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import csv
import tqdm
import warnings
warnings.filterwarnings('ignore')

print("Loading USE model...")
embed = hub.load("./use4")

print(sys.argv[1])

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

def createSchema(es):
    '''
        Creates a new index in the elastic search. 
        Defines appropriate schema for the index.
        We define 
            title         => text
            title_vector  => knn_vector
    
    '''
    
    #Refer: https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping.html
    # Mapping: Structure of the index
    # Property/Field: name and type  
    
    b = {
      "settings": {
        "index": {
          "knn": True,
          "knn.space_type": "cosinesimil"
        }
      },
      "mappings": {
        "properties": {
            "title":{
                "type":"text"
            },
          "title_vector": {
            "type": "knn_vector", # Helps to find approximate k nearest neighbours
            "dimension": 512
          }

        }
      }
    }

    ret = es.indices.create(index='questions-index', ignore=400, body=b)
    print(json.dumps(ret,indent=4))


def dataIngestion(es,NUM_QUESTIONS_INDEXED):
    '''
    This function helps us in ingesting the data into the
    elastic search index
    Here we index the title vector and the title.
    '''
    NUM_QUESTIONS_INDEXED=int(NUM_QUESTIONS_INDEXED)
    start_time = time.time()
    
    # Col-Names: Id,OwnerUserId,CreationDate,ClosedDate,Score,Title,Body
    cnt=0

    with open('Questions.csv', encoding="latin1") as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',' )
        next(readCSV, None)  # skip the headers 
        for row in (readCSV):
            doc_id = row[0];
            title = row[5];
            body = row[6]
            vec = tf.make_ndarray(tf.make_tensor_proto(embed([title]))).tolist()[0]

            b = {
                 "title":title,
                 "title_vector":vec,
                }

            res = es.index(index="questions-index", id=doc_id, body=b)

            cnt += 1
            if cnt%1000==0:
                print(cnt)

            if cnt == NUM_QUESTIONS_INDEXED:
                break;

        print("Completed indexing....")
    print("--- %s seconds ---" % (time.time() - start_time))
    print('****************************************************************************')



def main():

    es = connect2ES()
    createSchema(es)
    dataIngestion(es,sys.argv[1])


if __name__ == '__main__':
    main()