from pandas.io.json import json_normalize
from pprint import pprint
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
from itertools import combinations 
import numpy as np
from connect_mongo import make_client
import time
import pandas as pd

def calculate(table, element, mode, num):
      if mode == 'single' : 
            element = [element]
      print('function start')
      collection = make_client(table)
      print('mongo connect success')
      start = time.time()
      trans = make_medicodeList(collection, element, mode)
      print('medicodeList {}'.format(time.time() - start))
      start = time.time()
      df_freq, df_asso = calc_fpgrowth(trans, element, num)
      print('fpgrowth {}'.format(time.time() - start))
      return df_freq, df_asso

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
      
def calc_fpgrowth(df,element,min_support) :
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
      rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.5)
      rules['total_set'] = [frozenset.union(*X) for X in rules[['antecedents', 'consequents']].values]
      #rules=rules[rules["consequents"]==frozenset(element)]
      rules=rules[~rules['consequents'].apply(lambda x : x.isdisjoint(frozenset(element)))]
      #rules=rules[~rules["antecedents"].apply(lambda x : x.isdisjoint(frozenset(keyword)))]
      rules.sort_values(by=['confidence','antecedent support'],ascending=False,inplace=True) # 지지도 : (동시 포함 수) / (전체 수)
      rules["consequents"] = rules["consequents"].apply(lambda x : ', '.join(list(x)))
      rules["antecedents"] = rules["antecedents"].apply(lambda x: ', '.join(list(x)))
      #atc_df=pd.read_csv('code_list.csv',encoding='utf-8')
      #rules["consequents"] = rules["consequents"].apply(lambda x : ', '.join(list(map(lambda i : [atc_df['주성분코드'] == i].iloc[0]['Spec'], x))))
      #rules["antecedents"] = rules["antecedents"].apply(lambda x : ', '.join(list(map(lambda i : [atc_df['주성분코드'] == i].iloc[0]['Spec'], x))))
      rules['count']=len(df)*rules['support']
      rules['support']=100*rules['support']
      rules['confidence']=100*rules['confidence']
      rules['count']=rules['count'].apply(np.ceil)
      rules['count']=rules['count'].astype('int')
      rules['support']=rules['support'].round(2)
      rules=rules.loc[:,['antecedents','consequents','support','count','confidence','total_set']]
      rules.columns=['연관약품코드(전)','연관약품코드(후)','지지도(%)','출현빈도','연관도(%)','total_set']
      frequent_itemsets["total_set"]=frequent_itemsets["itemsets"] 
      frequent_itemsets["itemsets"] = frequent_itemsets["itemsets"].apply(lambda x : ', '.join(list(x)))
      ##rules["itemsets"] = rules["itemsets"].apply(lambda x : ', '.join(list(map(lambda i : [atc_df['주성분코드'] == i].iloc[0]['Spec'], x))))
      frequent_itemsets['support']=frequent_itemsets['support']*100
      frequent_itemsets['support']=frequent_itemsets['support'].round(2)
      frequent_itemsets=frequent_itemsets.loc[:,['itemsets','support','count','length','total_set']]
      frequent_itemsets.columns=['출현집합','지지도(%)','출현빈도','품목개수','total_set']
      frequent_itemsets.reset_index(drop=True)
      rules.reset_index(drop=True)
      return frequent_itemsets, rules

