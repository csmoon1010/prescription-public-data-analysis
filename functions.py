import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import warnings
import time

#방문횟수 카운트
def Visit_count(df):
    count = pd.DataFrame(df.groupby(['약품일반성분명코드'])['가입자일련번호'].value_counts()).rename(columns = {'가입자일련번호' : '방문횟수'})
    count = count.reset_index()
    #방문횟수가 3번이상인 사람부터 연산
    count = count[count['방문횟수'] > 2]
    count = count.drop(['약품일반성분명코드'], axis = 1)
    final = pd.merge(count, df, on = '가입자일련번호', how = 'left')
    final = final.drop_duplicates(['가입자일련번호', '요양개시일자', '약품일반성분명코드'])
    final = final.sort_values(['가입자일련번호', '요양개시일자']).reset_index().drop(['index'], axis = 1)
    return final


#처방일 간격 계산
def Calculate(df):
    # for문 _ 가입자별 요양 개시일자 창
    Date_dif_1 = df['요양개시일자'][1:].reset_index().drop(['index'], axis = 1).rename(columns = {'요양개시일자' : '처방일간격'})
    Date_dif_2 = df['요양개시일자'][0:].reset_index().drop(['index'], axis = 1).rename(columns = {'요양개시일자' : '처방일간격'})
    Date_dif = Date_dif_1 - Date_dif_2[:-1]
    final = pd.concat([df, Date_dif], axis = 1)
    final = final.reset_index()
    final = final.dropna(axis = 0)
    final = final.drop(['index'], axis = 1)
    return final

#날짜 type을 int로 변경(days 삭제)
# def Date_Number(df):
#     change = df['처방일간격'].astype(str).str.slice(0 , -24).astype(int)
#     data = df.drop(['처방일간격'], axis = 1)
#     final = pd.concat([data, change], axis = 1)
#     #마지막날 제거(단, 가장 마지막 성분은 이미 앞에서 제거됨)
#     last = final[-1:]
#     start = time.time()
#     final = final.groupby(["가입자일련번호"]).apply(lambda x : x.sort_values(["요양개시일자"], ascending=True)[:-1]).reset_index(drop=True)
#     final = pd.concat([final, last], axis = 0).reset_index(drop=True)
#     print(time.time()-start)
#     return final

def Date_Number(df):
    change = df['처방일간격'].astype(str).str.slice(0 , -24).astype(int)
    data = df.drop(['처방일간격'], axis = 1)
    final = pd.concat([data, change], axis = 1)
    #마이너스 제거
    final_del = final[final['처방일간격'] < 0].index
    final = final.drop(final_del)
    final = final.reset_index()
    final = final.drop(['index'], axis = 1)
    return final

#복약순응도 추정
def Medication(df): 
    df['복약순응도'] = round((df['총투여일수']/df['처방일간격'])*100, 2)
    df['복약순응도'].loc[df['복약순응도'] > 100] = 100
    mean = df.groupby('가입자일련번호')['복약순응도'].mean()
    #환자별 평균복약순응도 산출
    df['평균복약순응도'] = round(df['가입자일련번호'].map(mean), 2)
    df['순번'] = range(1, len(df) + 1)
    final = df[['순번', '약품일반성분명코드', '가입자일련번호', '처방내역일련번호', '방문횟수', '요양개시일자', '1일투약량', '총투여일수', '처방일간격', '복약순응도', '평균복약순응도']]
    return final

def Statistics(df) :
    data = [["평균", df['1일투약량'].mean(), df['총투여일수'].mean(),df['처방일간격'].mean(), df['복약순응도'].mean()],
    ["최빈값", df['1일투약량'].mode(), df['총투여일수'].mode(),df['처방일간격'].mode(), df['복약순응도'].mode()]]
    final = pd.DataFrame(data, columns = ["구분", "1일투약량", "총투여일수", "처방일간격", "복약순응도"])
    print(final)
    return final

#복약순응도 결과정리(처방건수기준)
def display_1(df):
    fig = plt.figure() # figsize = [12, 6]
    fig = plt.title('복약순응도 시각자료(처방건수)')
    fig = sns.distplot(df['복약순응도'], color='blue', label = '복약순응도')
    # final = df['복약순응도'].describe([.10, .20, .30, .40, .60, .70, .80, .90])
    # final = final.astype(int)
    return fig
