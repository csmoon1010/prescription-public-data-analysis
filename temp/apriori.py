# -*- coding: utf-8 -*-
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.figure_factory as ff
import plotly.graph_objects as go
import pandas as pd
import pymongo
from pymongo import MongoClient
import json
import dash_table
import time
import yaml
from sshtunnel import SSHTunnelForwarder
from pandas.io.json import json_normalize
from pprint import pprint
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules
from itertools import combinations 
import numpy as np
import matplotlib.pyplot as plt
#import modin.pandas as mp

MONGO_HOST = "210.117.182.242"
MONGO_PORT = 27017
MONGO_DB = "daewoong"
MONGO_USER = "dblab"
MONGO_PASS = "dbl5511!@"
server = SSHTunnelForwarder(
    MONGO_HOST,
    ssh_username=MONGO_USER,
    ssh_password=MONGO_PASS,
    remote_bind_address=('127.0.0.1', 27017)
)
server.start()
client = pymongo.MongoClient('127.0.0.1', server.local_bind_port,serverSelectionTimeoutMS=200000)
db = client[MONGO_DB]
collection = db.get_collection('medicodeset')
print("make query")
checklist=["421001ATB"]
### 단일처방 ###
# cursor=collection.aggregate(pipeline=[
#     { '$project' : { '_id' : 0 , 'medicode' : 1 } } 
#     ], allowDiskUse=True
# )
### OR 조건 ###
# cursor=collection.aggregate(pipeline=[
#   {
#     "$group": {
#       "_id": "$처방내역일련번호",
#       "medicode": {
#         "$addToSet": "$약품일반성분명코드"
#       }
#     }
#   },
#   {
#     "$match" : {
#       "medicode":{
#         "$in": ["438901ATB","186101ATB"]
#         } 
#     }
#   },
#   {
#     "$project" : { '_id' : 0 , 'medicode' : 1 }
#   }
# ], allowDiskUse=True
# )
### AND 조건 ###
# cursor=collection.aggregate(pipeline=[
#   {
#     "$group": {
#       "_id": "$처방내역일련번호",
#       "medicode": {
#         "$addToSet": "$약품일반성분명코드"
#       }
#     }
#   },
#   {
#     "$match" : {
#       "medicode":{
#         "$all": ["438901ATB","186101ATB"]
#         } 
#     }
#   },
#   {
#     "$project" : { '_id' : 0 , 'medicode' : 1 }
#   }
# ], allowDiskUse=True
# )
### set DB ###
# cursor=collection.aggregate(pipeline=[
#   {
#     "$match" : {
#       "medicode":{
#         "$all": ["438901ATB","186101ATB"]
#         } 
#     }
#   },
#   {
#     "$project" : { '_id' : 0 , 'medicode' : 1 }
#   }
# ], allowDiskUse=True
# )
start=time.time()
cursor=collection.aggregate(pipeline=[
  {
    "$match" : {
      "medicode":{
         "$in": checklist
         }
    }
  },
  {
    "$project" : { '_id' : 0 , 'medicode' : 1 }
  }
], allowDiskUse=True
)
print(time.time()-start)
print("make list")
start=time.time()
trans=json_normalize(cursor)
print(time.time()-start)
_trans=list(trans['medicode'])

# 원-핫 인코딩
te = TransactionEncoder()
te_ary = te.fit(_trans).transform(_trans)
df = pd.DataFrame(te_ary, columns=te.columns_)
print("get frequent itemsets")

# Apriori 알고리즘
start=time.time()
frequent_itemsets = apriori(df, min_support=0.01,use_colnames=True,verbose=1)
print(time.time()-start)
frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
# for i in range(1,len(checklist)+1):
#   for subset in combinations(checklist,i):
#     frequent_itemsets=frequent_itemsets[frequent_itemsets['itemsets']!= frozenset(subset)]
frequent_itemsets.sort_values(by='support',ascending=False,inplace=True)
frequent_itemsets.head()
print("get frequent itemsets")

# association_Rule
start=time.time()
rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.1)
print(time.time()-start)
# for i in range(1,len(checklist)):
#   for subset in combinations(checklist,i):
#     rules=rules[rules['antecedents']!= frozenset(subset)]
rules.sort_values(by='confidence',ascending=False,inplace=True) #신뢰도 : (a, b 동시 포함 수) / (a 입력한 항목이 포함될 수)
rules.sort_values(by='antecedent support',ascending=False,inplace=True) # 지지도 : (동시 포함 수) / (전체 수)
rules.head(n=15)

# fit = np.polyfit(rules['lift'], rules['confidence'], 1)
# fit_fn = np.poly1d(fit)
# plt.plot(rules['lift'], rules['confidence'], 'yo', rules['lift'], fit_fn(rules['lift']))

# frequent_itemsets.sort_values(by='support',ascending=False,inplace=True)
# frequent_itemsets.sort_values(by='length',ascending=False,inplace=True)
# frequent_itemsets.head()

