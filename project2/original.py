# from django.shortcuts import render
# from django.http import HttpResponse
import pandas as pd
import numpy as np
from itertools import chain, combinations
import operator
import time
from io import BytesIO

# 필요한 파일 불러오기
nhis = pd.read_csv('NHIS.csv', low_memory=False)
atc = pd.read_csv('atc2020_June.csv', encoding='euc-kr')

# Create your views here.
def search(request):
    print("search") #디버그용

    #인풋 받아오기
    element = request.GET.get('element')
    filtering = request.GET.get('filtering')
    function = request.GET.get('function')
    wanted_e = request.GET.get('wanted_e')
    top_num = request.GET.get('top_num')
    top = request.GET.get('top')

    #주성분코드 -> 원하는 형태로 리스트에 넣어주기 (conditions 함수)  
    e = conditions(element)

    # 리스트에 들어있는 성분의 길이로 복수성분인지 단일 성분인지 구분
    # 복수 성분일 경우, filtering 변수에 있는 값 (1 또는 2 일텐데 1 AND / 2 OR 차이임)에 따라 dataCall (데이터 호출)
    if len(e) > 1:
        request = filtering
        data_info = "복수성분"
    else:
        request = 3
        data_info = "단일성분"
    
    #데이터 호출
    d = dataCall(nhis, e, request)

    # 만약 원하는 데이터 속에서 성분을 한정해 패턴을 추출하고자 하는 경우라면 이전에 불러온 데이터에서 한 번 더 데이터 추출해내기 
    if function == "3":
        d = dataCall(d, wanted_e, "1") #추가 성분이 모두 들어있는 데이터 추출
        d = d[d.약품일반성분명코드.isin(e)] #그 데이터에서 내가 가장 처음에 알고자 했던 성분이 있는 경우 추출
        p = d.groupby("처방내역일련번호")['약품일반성분명코드'].apply(set)
        p = list(p)
        print("해당 조건의 전체 처방전 개수 : {0}".format(len(p)))
    else:
        p = listCall(d, e)

    # 데이터 0개이면 끝
    if len(p) == 0:
        print("처방전 0개 - 종료")
        return
    
    # 조합 추출하는 함수
    ## 다시 이해해보기
    r = funcCall_comb(d, p, e, atc, function, top)

    # 원하는 랭크만큼 추출하는 함수
    r = topFrequency(r, p, top_num)

    # 결과값 html화하는 함수
    html = write_to_html_file(r, element, data_info)
    return HttpResponse(html)


# 첫번째 장 -> 두번째 장 (결과값) html 작성하는 함수
def write_to_html_file(df, e, di, filename='result.html'):
    df_html = df.to_html(index=False, justify='center', table_id="df") #판다스의 to_html 함수를 활용
    result = '''
                <!DOCTYPE html>
    <html lang="ko">
    <head>
    
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css?family=Nanum+Gothic:400,700,800&amp;subset=korean" rel="stylesheet">
        <style>
          p {
            font-family: "Nanum Gothic", sans-serif;
          }
          p.a {
            font-weight: 400;
          }
          p.b {
            font-weight: 700;
          }
          p.c {
            font-weight: 800;
          }
          p.d {
            font-weight: bold;
          }
          table, th, td {
           border: 1px solid black;
           border-collapse: collapse;
           }
          th, td {
           padding: 5px;
           text-align: center;
           font-family: "Nanum Gothic", sans-serif;
           font-size: 90%;
           }
           table tbody tr:hover {
           background-color: #dddddd;
           }
           

        </style>
    
    
        <title>DW Project</title>
    
    
    <body>
        <header>
            <img src="/static/img/대웅제약.jpg" height = "50">
            <h1> <p class = "c"> 병용처방 패턴파악 </h1>
        </header>
        
        <form action="/dwproject", method = "get">
            <p>
                <button type="submit">첫 페이지로 돌아가기</button>
            </p>
        </form>
        
        <p><h2> <p class="b"> 결과 </h2>
            
        </p>
        
    '''

    result += df_html # 더해주기
    result += '''
        
    </body>
    </html>
    '''

    return result

def pattern(request):
    return render(request,'pattern.html')



#############################################
#############################################
#########전처리 및 패턴 추출 함수 #############
#############################################
#############################################


#####################################
############전처리 함수들############
#####################################

# 주성분코드 리스트로 반환하는 함수 (처음 입력 시엔 스트링이나 그 이후 과정에서 리스트 형태로 입력될 때가 있어 이 함수를 만들었던 것으로 기억)
# 그래서 결론적으로 스트링 -> 리스트 시키는 함수 / 이미 리스트화 잘 되어있다면 그대로 내버려두는 함수
def conditions(e):
    if type(e) == str:  # 421001ATB, 619101ATB
        try:
            conditions = listSplit(e)
        except:
            conditions = e
    elif type(e) == list:
        conditions = e
    return conditions

# conditions에서 사용되는 전처리 함수
def listSplit(l):
    ls = l.split(",") 
    if len(ls) == 1: # 만약 ,로 구분되어 있지 않다면 띄어쓰기로 스플릿
        ls = l.split()
    ls = [i.strip() for i in ls] #좌우 공백 삭제 
    return ls # 공백도 없고 성분만 딱 들어있는 리스트 리턴



# 싱글 엘리먼트에 대한 데이터 추출 (특정 성분 한 개가 있는 데이터 추출)
def single_e_data(data, e):  # e는 원하는 성분
    data = data.dropna(axis=0)
    # 해당 성분이 있는 row 데이터 프레임에서 가지고 오기
    df = data[data.약품일반성분명코드.isin(e)]

    # 가져온 데이터 프레임에서 유니크한 처방전 넘버 가지고 오기
    presnum = df['처방내역일련번호'].unique()

    # 처방전 넘버에 해당하는 데이터 가져오기 (해당 성분 + 해당 성분 X)
    pres = data[data.처방내역일련번호.isin(presnum)]

    return pres


# 멀티플 엘리먼트에 대한 데이터 추출 (특정 성분 여러 개가 있는 데이터 추출)
def multiple_e_data(data, e, ANDorOR):  # e는 len 2 이상의 원하는 성분 리스트
    data = data.dropna(axis=0)

    e = conditions(e)

    # 데이터 뽑아내는 조건 저장하는 집합
    finalCondition = set()

    # ANDorOR
    if ANDorOR == "AND": #AND라면
        for i in range(len(e)): #복수 성분이므로 반복문 돌아줌
            if i == 0: #처음 시작할 때, 내가 원하는 주성분코드가 들어있으면 그 처방전 번호 finalCondition에 저장해주기
                finalCondition.update(list(data[data.약품일반성분명코드 == e[i]]['처방내역일련번호'].unique()))
            else: #그 다음 주성분코드부터는 이전 주성분코드가 들어있던 처방전과의 교집합을 구해주기
                finalCondition = finalCondition.intersection(list(data[data.약품일반성분명코드 == e[i]]['처방내역일련번호'].unique()))
    else:  # OR
        for i in range(len(e)): #복수 성분이므로 반복문 돌아줌
            finalCondition.update(list(data[data.약품일반성분명코드 == e[i]]['처방내역일련번호'].unique())) #그냥 계속 합집합

    #반복문을 돌고 난 후 저장된 최종 처방전 번호들 -> 그 처방전 들어있는 데이터만 추출
    pres = data[data.처방내역일련번호.isin(finalCondition)] 
    return pres


# 해당 데이터에 존재하는 처방전 별 병용처방 성분 추출 (내가 입력한 성분 제외하고 같이 처방된 성분들 뽑아내는 과정)
def pList(pres, e):
    e = conditions(e)

    # 병용처방성분 (추출한 처방전 데이터 중 해당 성분 아닌 성분) 목록 가지고 오기
    presnon = pres[~pres.약품일반성분명코드.isin( e)]

    pList = presnon.groupby("처방내역일련번호")['약품일반성분명코드'].apply(set)
    pList = list(pList)

    return pList





########################################
############부분 조합 함수들############
########################################

# 조합 함수 - 집합으로 반환
# m은 nCm 을 뜻함
def combination(iterable, m):
    s = set(iterable)
    return set(combinations(s, m))

# makeCombSet을 위한 함수 : 누적 조합 찾기 (함수) - 이전 조합 + 새로운 조합 = 집합으로 반환
def findCombination(com, prlist, m):
    com.update(combination(prlist, m))
    return com


# 전체 처방전에 대한 누적 조합 찾기 - 집합으로 반환
def makeCombSet(prlist, m):
    c = set()
    for i in range(len(prlist)):
        findCombination(c, prlist[i], m)
    return c

# 뽑아낸 조합에 대한 횟수를 세기 위한 함수
def makeCombDict(prlist, d_key, m):
    result = {}  # 저장할 딕셔너리 만들어주기

    # 전체 조합에 대한 Key 생성 - 각각의 Value 0으로 초기화
    for i in range(len(d_key)):
        result["{0}".format(d_key[i])] = 0

    # 각 처방전 마다 있는 모든 조합 정렬 후 그 키에 해당하는 카운트 +1
    for i in range(len(prlist)):
        ps = combination(prlist[i], m)  # 현재 처방전에서 나올 수 있는 모든 조합 담긴 리스트
        pslist = list(ps)
        dictkey = sorted(list(map(sorted, pslist)))  # 만들어준 리스트 내부 각각의 리스트들을 정렬 그리고 전체 또 정렬 (just in case)
        for j in range(len(dictkey)):
            result["{0}".format(dictkey[j])] += 1
    return result

# 만들어놓은 함수를 실행하고 어느 단계까지 왔는지 확인하기 위한 함수
def comb(plist, m):
    CombSet = makeCombSet(plist, m)
    print('Step 1 : Making nC{0} Possible Combinations done'.format(m))
    dictKey = makeListForDict(CombSet)
    print('{0} done'.format("Step 2 : Making a List for a Dictionary"))
    prResult = makeCombDict(plist, dictKey, m)
    print('{0} done'.format("Step 3 : Making Dictionary"))
    prResult_sorted = sortDict(prResult)
    print('{0} done'.format("Step 4 : Making a Sorted Dictionary"))
    return prResult_sorted


########################################
############전체 조합 함수들############
########################################

# 멱집합 함수 - 집합으로 반환
def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = set(iterable)
    return set(chain.from_iterable(combinations(s, r + 1) for r in range(len(s) + 1)))


# makeAllPower을 위한 함수 : 누적 조합 찾기 (함수) - 이전 조합 + 새로운 조합 = 집합으로 반환
def makePower(com, prlist):
    com.update(powerset(prlist))
    return com


# 전체 처방전에 대한 누적 조합 찾기 - 반복문 돌면서 최종 조합 반환
def makeAllPower(prlist):
    c = set()
    for i in range(len(prlist)):
        makePower(c, prlist[i])
    return c

# 뽑아낸 조합에 대한 횟수를 세기 위한 함수
def makePowerDict(prlist, d_key):
    result = {}  # 저장할 딕셔너리 만들어주기

    # 전체 조합에 대한 Key 생성 - 각각의 Value 0으로 초기화
    for i in range(len(d_key)):
        result["{0}".format(d_key[i])] = 0

    # 각 처방전 마다 있는 모든 조합 정렬 후 그 키에 해당하는 카운트 +1
    for i in range(len(prlist)):
        ps = powerset(prlist[i])  # 현재 처방전에서 나올 수 있는 모든 조합 담긴 리스트
        pslist = list(ps)
        dictkey = sorted(list(map(sorted, pslist)))  # 만들어준 리스트 내부 각각의 리스트들을 정렬 그리고 전체 또 정렬 (just in case)
        for j in range(len(dictkey)):
            result["{0}".format(dictkey[j])] += 1
    return result

# 만들어놓은 함수를 실행하고 어느 단계까지 왔는지 확인하기 위한 함수
def power(plist):
    PowerSet = makeAllPower(plist)
    print('{0} done'.format("Step 1 : Making All Possible Combinations"))
    dictKey = makeListForDict(PowerSet)
    print('{0} done'.format("Step 2 : Making a List for a Dictionary"))
    prResult = makePowerDict(plist, dictKey)
    print('{0} done'.format("Step 3 : Making Dictionary"))
    prResult_sorted = sortDict(prResult)
    print('{0} done'.format("Step 4 : Making a Sorted Dictionary"))
    return prResult_sorted


###################################
############호출 함수들############
###################################

# 데이터 호출 함수
def dataCall(rawdata, element, request):
    # 복수성분 병용처방
    if request == "1":  # AND
        data = multiple_e_data(rawdata, element, "AND")
    elif request == "2":  # OR
        data = multiple_e_data(rawdata, element, "OR")
    else:  # 단일성분 병용처방
        data = single_e_data(rawdata, element)
    print("데이터 추출 완료")
    return data

# 처방전 리스트 호출 함수
def listCall(data, element):
    plist = pList(data, element)
    print("처방전 추출 완료")
    print("해당 조건의 전체 처방전 개수 : {0}".format(len(plist)))
    return plist

# 조합 추출 호출 함수
def combCall(plist, request):
    if type(request) == int:  # nC1
        result = comb(plist, request)
    elif request == "n":
        result = power(plist)
    return result



###################################
############공통 함수들############
###################################


# 딕셔너리 카운트 수대로 정렬
def sortDict(combDict):
    sortedDict = sorted(combDict.items(), key=operator.itemgetter(1), reverse=True)
    return sortedDict


# 딕셔너리를 만들어 주기 위해 인덱싱 부여 필요 - 리스트로 반환
def makeListForDict(CombSet):
    clist = list(CombSet)  # 집합 to 리스트
    d_key = sorted(list(map(sorted, clist)))  # 만들어준 리스트 내부 각각의 리스트들을 정렬 그리고 전체 또 정렬 (just in case)
    return d_key  # 딕셔너리 키 리스트 반환

# 보여주기 위한 프린트 함수,,,인데 필요한지 잘 모르겠긴 함 (디버그용 + 확인용)
def printDict(sortedDict):
    for i in range(top_num):
        print("{0} count {1}".format(sortedDict[i][0], sortedDict[i][1]))


# 상위 몇 가지 조합을 보고 싶은지 물어보는 함수
def topFrequency(sortedDict, p, top_num):
    try:
        rd = resultToDF(sortedDict, p)
        top_num = int(top_num)
        #top_num = int(input("상위 몇 개의 조합? : "))
        if top_num > len(rd):
            top_num = len(rd)
            print("원하시는 상위 성분 조합 개수보다 병용 조합 수가 작아 전체 조합을 출력합니다")
        return rd[:top_num]
    except:
        print("병용 처방 기록이 없습니다")
        return None

# 데이터프레임화 시켜주는 함수 (데이터프레임으로 만들어주기 위한 전처리 함수)
def resultToDF(r, p):
    rd = pd.DataFrame(r)
    rd = rd.rename(columns={0: '주성분코드', 1: 'count', 2: 'Spec'})
    rd['주성분코드'] = rd['주성분코드'].astype(str).str.slice(1, -1)
    rd['Spec'] = rd['Spec'].astype(str).str.slice(1, -1)
    rd['주성분코드'] = rd.주성분코드.str.replace("'", "")
    rd['Spec'] = rd['Spec'].str.replace("'", "")
    rd['Total Prescription'] = len(p)
    rd = rd[['주성분코드', 'Spec', 'count', 'Total Prescription']]
    return rd


# 뽑아낸 최종 조합에 대한 설명 덧붙여주는 함수 (atc 파일 활용)
def nameChange(result, atc):
    result = list(map(list, result))

    for i in range(len(result)):
        result[i].append(list(atc[atc['주성분코드'].isin(eval(result[i][0]))]['Spec']))

    return result

# 최최최최종 함수 : 전체 실행용 함수
def funcCall_comb(data, plist, e, atc, request, top):
    # 단일성분 기준 조합 추출
    if request == "1":
        try:
            top = int(top) #스트링인 경우가 있어서 한번 해줬던 것 같은데 불필요하면 삭제 可
        except:
            print("선택하신 만큼보다 작은 병용처방 성분이 있어, 전체로 계산합니다")
            top = None
        print("--------------------------------------------------")
        topdict = combCall(plist, 1)[:top]
        print("top {0} 단일병용처방 빈도 계산 중".format(top))
        toplist = [topdict[i][0][2:-2] for i in range(len(topdict))]
        print("--------------------------------------------------")
        print("top {0} 단일병용처방 조합".format(top))
        print(nameChange(topdict, atc))
        print("--------------------------------------------------")
        print("top {0} 단일병용처방이 들어간 전체 조합 빈도 계산 중".format(top))
        datatop = multiple_e_data(data, toplist, "OR")
        datatop = datatop[datatop.약품일반성분명코드.isin(toplist)]
        plisttop = listCall(datatop, e)
        result = combCall(plisttop, "n")
        result = nameChange(result, atc)

    # 전체조합 추출
    elif request == "2":
        print("병용처방 전체조합 다빈도 계산 중")
        result = combCall(plist, "n")
        result = nameChange(result, atc)

    # 선택한 조합 한정 조합 추출
    elif request == "3":
        print("선택하신 조합 다빈도 계산 중")
        result = combCall(plist, "n")
        result = nameChange(result, atc)

    print("--------------------------------------------------")
    return result
