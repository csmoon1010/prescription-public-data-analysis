from pandas.io.json import json_normalize
from pprint import pprint
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
from itertools import combinations 
import numpy as np
from connect_mongo import make_client
import time
import pandas as pd

def calculate(table, element, mode, num) :
      if mode == 'single' : 
            element = [element]
      print('function start')
      collection = make_client(table)
      print('mongo connect success')
      start = time.time()
      trans = make_medicodeList(collection, element, mode)
      print('medicodeList {}'.format(time.time() - start))
      start = time.time()
      df = calc_apriori(trans, element, num)
      print('fpgrowth {}'.format(time.time() - start))
      return df

def make_medicodeList(collection, element, mode) :
      if mode == 'AND' :
            cursor=collection.aggregate(pipeline=[
            {
              "$match" : {
                "medicode":{
                  "$all" : element
                  }
              }
            },
            {
              "$project" : { '_id' : 0 , 'medicode' : 1 }
            }
            ], allowDiskUse=True
            )
      else :
            # if (str(type(element)) == "<class 'str'>"):
            #       element = [element]
            cursor=collection.aggregate(pipeline=[
            {
              "$match" : {
                "medicode":{
                  "$in" : element
                  }
              }
            },
            {
              "$project" : { '_id' : 0 , 'medicode' : 1 }
            }
            ], allowDiskUse=True
            )
      print('make cursor')
      df=pd.DataFrame.from_dict(cursor)
      if len(df)==0:
            return []
      df=list(df['medicode'])
      print('get data')
      print(df[:5])
      return df

def get_element(df) :
      result = ""
      for l in df["antecedents"] :
            result = result + ", " + l
      return result
      
def calc_apriori(df,element,min_support) :
      # 원-핫 인코딩
      te = TransactionEncoder()
      te_ary = te.fit(df).transform(df)
      df = pd.DataFrame(te_ary, columns=te.columns_)
      print(df.head())
      # fpgrowth
      print("get frequent set by min support =",min_support/100)
      frequent_itemsets = fpgrowth(df, min_support=min_support/100, use_colnames=True, verbose=1)
      frequent_itemsets['length'] = frequent_itemsets['itemsets'].apply(lambda x: len(x))
      frequent_itemsets['count']=len(df)*frequent_itemsets['support']
      frequent_itemsets['count']=frequent_itemsets['count'].apply(np.ceil)
      frequent_itemsets['count']=frequent_itemsets['count'].astype('int')
      frequent_itemsets.sort_values(by=['support','length'],ascending=False,inplace=True)
      print(frequent_itemsets.head())

      # association rule
      rules = association_rules(frequent_itemsets, metric="support", min_threshold=min_support/100)
      #rules=rules[rules["consequents"]==frozenset(element)]
      rules=rules[~rules["consequents"].apply(lambda x : x.isdisjoint(frozenset(element)))]
      #rules=rules[~rules["antecedents"].apply(lambda x : x.isdisjoint(frozenset(keyword)))]
      rules.sort_values(by=['confidence','antecedent support'],ascending=False,inplace=True) # 지지도 : (동시 포함 수) / (전체 수)
      rules["antecedents"] = rules["antecedents"].apply(lambda x: ', '.join(list(x)))
      rules["consequents"] = rules["consequents"].apply(lambda x : ', '.join(list(x)))
      rules['count']=len(df)*rules['support']
      rules['support']=100*rules['support']
      rules['confidence']=100*rules['confidence']
      rules['count']=rules['count'].apply(np.ceil)
      rules['count']=rules['count'].astype('int')
      rules=rules.loc[:,['antecedents','support','count','confidence']]
      rules.columns=['연관약품코드','지지도 ( % )','빈도 ( 횟수 )','연관도 ( % ) ']
      print(rules.shape[0])
      return rules

