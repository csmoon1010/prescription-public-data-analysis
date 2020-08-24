import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State, MATCH, ALL
from pymongo import MongoClient
import pandas as pd
import pprint
import numpy as np
from sshtunnel import SSHTunnelForwarder
import functions2
from connect_mongo import make_client
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth

def get_atc() :
    atc = make_client('atc')
    atc_df = pd.DataFrame.from_dict(atc.find())
    atc_code = atc_df['주성분코드'].tolist()
    atc_spec = atc_df['Spec'].tolist()
    return [atc_code, atc_spec]

def get_top(atc_list, selected) :
    result = []
    for a,b in zip(atc_list[0], atc_list[1])  :
        if(a not in(selected)) :
            result.append({'label' : a+' : '+b, 'value' : a})
    return result

def make_table(table, element, mode, num) :
    if table == None :
        df = pd.DataFrame()
    else : df = functions2.calculate(table, element, mode, num)
    return [[{"name" : i, "id" : i} for i in df.columns], df.to_json(orient='split')]
      

def create_dashboard2(server) :
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard2/', external_stylesheets=external_stylesheets)
    selected = []
    PAGE_SIZE = 10
    atc_list = get_atc()
    app.layout = html.Div([
        html.H3(id = 'title', children = '병용처방 패턴파악 대시보드'),
        html.Div(id = 'condition', children = [
            html.Div(children = '데이터 필터링 조건'),
            html.Div(id = 'dropdowns', children = [
                dcc.Dropdown(id = 'select1',
                    options=[
                        {'label' : '단일', 'value' : 'single'},
                        {'label' : '복수', 'value' : 'multi'}],
                    placeholder='성분 개수', searchable=False
                ),
                dcc.Dropdown(id = 'select2', searchable=False),
                dcc.Dropdown(id = 'elements',
                    options = [{'label' : a+' : '+b, 'value' : a} for a, b in zip(atc_list[0], atc_list[1])],
                    placeholder = '원하는 성분 선택', disabled = True, multi = True, value = None
                )], style = {'width' : '35%'})
        ], style = {"margin-bottom" : "25px"}),
        html.Div(id = 'combination', children = [
            html.Div(children = '조합 선택'),
            dcc.RadioItems(id = 'radio_main',
                options=[
                    {'label' : '기본', 'value' : 'all'},
                    {'label' : 'top 단일병용처방 성분이 들어간 다빈도 조합', 'value' : 'top'},
                    {'label' : '추출한 데이터에 특정 성분만 들어간 조합', 'value' : 'filter'}],
                value = 'all', labelStyle={'display' : 'inline-block'}
            ),
            html.Div(id = 'radio_sub', children = [
                html.Div(id = 'sub_explain', children = '데이터 필터링 조건을 먼저 선택하세요.'),
                dcc.Input(
                    id = 'sub_input',type = 'number', min = 10, 
                    debounce = True, placeholder='개수를 입력하세요', style = {'display' : 'none'}),
                dcc.Dropdown(
                    id = 'sub_drop', options = [],
                    placeholder = '특정 성분 선택', style = {'display' : 'none'})
            ])
        ], style = {"margin-bottom" : "25px"}),
        html.Div(id = 'result', children = [
            html.Div(children = '지지도 입력'),
            dcc.Slider(
                id='num',
                min=0.001,
                max=100,
                step=0.001,
                value=10,
                included=False,
                marks= {
                    i: str(i)+'%' for i in range(10,101,10)
                }
            )
        ]),
        html.Button('Submit', id = 'submit_button', n_clicks = 0), 
        html.Br(),
        dcc.Loading(
            id="loading-table",
            type="default",
            children=html.Div(id = 'table', children = dt.DataTable(id = 'datatable-paging',
            page_current = 0,
            page_size = PAGE_SIZE,
            page_action = 'custom'), style = {'display' : 'none','width':'40%'})
        ),
        html.Div(id = 'intermediate_atc', style = {'display' : 'none'}),
        html.Div(id = 'intermediate', style = {'display' : 'none'})
    ])
    init_callback(app, atc_list)
    return app

def init_callback(app, atc_list) :
    # UI 작동
    @app.callback(
        [Output('select2', 'options'), Output('select2', 'placeholder'), Output('select2', 'disabled'), Output('select2', 'value')],
        [Input('select1', 'value')]
    )
    def update_select2(value) :
        if value == 'single' :
            op = [{'label' : '단일성분', 'value' : 'single'}]
            return [op, '===선택===', False, None]
        elif value == 'multi' :
            op = [
                {'label' : '해당 성분 모두 포함(AND)', 'value' : 'AND'},
                {'label' : '해당 성분 중 한 가지 이상 포함(OR)', 'value' : 'OR'}
            ]
            return [op, '===선택===', False, None]
        else :
            op = []
            return [op, '데이터 필터링 조합을 선택해주세요', True, None]


    @app.callback(
        [Output('elements', 'disabled'), Output('elements', 'multi'), Output('elements', 'value')],
        [Input('select1', 'value'), Input('select2', 'value')],
        [State('elements', 'value')]
    )

    def update_elements(selected1, selected2, original) :
        if selected2 == None :
             result = [True, False, None]
        else :
            if  selected1 == 'single' :
                result = [False, False, None]
            elif selected1 == 'multi' :
                result = [False, True, original]
            else :
                result = [True, False, None]
        return result

    @app.callback(
        [Output('sub_explain', 'style'), Output('sub_input', 'style'), Output('sub_drop', 'style'), Output('sub_drop', 'options')],
        [Input('radio_main', 'value'), Input('elements', 'value')]
    )
    def update_radio_sub(value, selected) :
        result = [{'display' : 'none'}, {'display' : 'none'}, {'display' : 'none'}, []]
        if selected == None :
            result =  [{'display' : 'block'}, {'display' : 'none'}, {'display' : 'none'}, []]
        else :
            if value == 'top' :
                result =  [{'display' : 'none'}, {'display' : 'block'}, {'display' : 'none'}, []]
            elif value == 'filter' :
                result =  [{'display' : 'none'}, {'display' : 'none'}, {'display' : 'block'}, get_top(atc_list, selected)]
        return result

    @app.callback(
        Output('num', 'disabled'),
        [Input('radio_main', 'value'), Input('sub_input', 'value'), Input('sub_drop', 'value')]
    )
    def update_result(r_main, sub_i, sub_d) :
        result = []
        if(r_main != 'all') :
            if(sub_i != None or sub_d != None) :
                result = False
            else :
                result = True
        else : result = False
        return result
    
    # 버튼에 따라 기능 구현 callback
    # 필수 - submit 버튼 - elements(선택한 약품성분코드), select2(and,or,단일), radio_main(조합선택번호), result(표현한 개수)
    # 선택적 - 조합선택 1 - 개수 / 조합선택 3 - 입력한 성분 하나
    #output : 함수 결과

    @app.callback(
        [Output('datatable-paging', 'columns'), Output('intermediate', 'children'), Output('table', 'style')], 
        [Input('submit_button', 'n_clicks')],
        [State('elements', 'value'), State('select2', 'value'),
        State('radio_main', 'value'), State('sub_input', 'value'),
        State('sub_drop', 'value'),State('num', 'value')]
    )
    def update_table(n_clicks, element, mode, r_main, sub_i, sub_d, num) :
        print('update')
        result = []
        if num != None : 
            if r_main == 'all' :
                result = make_table('medicodeset', element, mode, num) + [{'display' : 'inline'}]
        else : 
            result = make_table(None, element, mode, num) + [{'display' : 'none'}]
        return result

    @app.callback(
        Output('datatable-paging', 'data'),
        [Input('datatable-paging', "page_current"),
        Input('datatable-paging', "page_size"),
        Input('intermediate', 'children')]
    )
    def update_paging(page_current, page_size, data) :
        df = pd.read_json(data, orient='split')
        return df.iloc[
            page_current*page_size : (page_current + 1) * page_size
        ].to_dict('records')

