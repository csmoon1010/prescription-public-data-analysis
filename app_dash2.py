import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from pymongo import MongoClient
import pandas as pd
import pprint
import numpy as np
import functions2
from connect_mongo import make_client
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
import time

PAGE_SIZE = 10
df_freq=pd.DataFrame()
df_asso=pd.DataFrame()


def get_atc() :
    atc_df=pd.read_csv('code_list.csv',encoding='utf-8')
    #atc = make_client('atc')
    #atc_df = pd.DataFrame.from_dict(atc.find())
    atc_code = atc_df['주성분코드'].to_list()
    atc_spec = atc_df['Spec'].to_list()
    return [atc_code, atc_spec]

def get_top(atc_list, selected) :
    result = []
    for a,b in zip(atc_list[0], atc_list[1])  :
        if(a not in(selected)) :
            result.append({'label' : a+' : '+b, 'value' : a})
    return result

def make_table(table, element, mode, num) :
    global df_freq,df_asso
    if table == None :
        df_freq = pd.DataFrame()
        df_asso = pd.DataFrame()
    else :
        df_freq, df_asso = functions2.calculate(table, element, mode, num)
    return [[{"name" : i, "id" : i} for i in df_freq.columns if i!='total_set'], len(df_freq)//PAGE_SIZE + 1, [{"name" : i, "id" : i} for i in df_asso.columns if i!='total_set'], len(df_asso)//PAGE_SIZE + 1]
      

def create_dashboard2(server) :
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard2/', external_stylesheets=external_stylesheets)
    selected = []
    atc_list = get_atc()
    app.layout = dbc.Container(
        fluid=True,
        children=[
            html.H1("공공데이터 기반 연관 약품 분석 (빈도/관련도)"),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col([dbc.Card([
                        dbc.Label('단일/복합처방 선택'),
                        dcc.Dropdown(id = 'select1',
                            options=[
                                {'label' : '단일', 'value' : 'single'},
                                {'label' : '복수', 'value' : 'multi'}],
                            placeholder='성분 개수', searchable=False
                        ),
                        dbc.Label('AND/OR 조건선택'),
                        dcc.Dropdown(id = 'select2', searchable=False),
                        dbc.Label('품목선택'),
                        dcc.Dropdown(id = 'elements',
                            options = [{'label' :  str(a)+' : '+str(b), 'value' : str(a)} for a, b in zip(atc_list[0], atc_list[1])],
                            placeholder = '원하는 성분 선택', disabled = True, multi = True, value = None,
                            optionHeight=80,
                        ),
                        dbc.Label('지지도 설정'),
                        dcc.Slider(
                            id='num',
                            min=0.01,
                            max=40,
                            step=0.01,
                            value=10,
                            included=False,
                            marks= {
                                i: str(i)+'%' for i in range(10,41,10)
                            }
                        ),
                        html.Br(),
                        dbc.Button("연관 품목 조회",id="submit_button", n_clicks=0, color="primary", outline=True, block=True,loading_state={'is_loading':True}),
                        html.Br(),
                        dbc.Spinner(html.Div(id="alert-msg"))
                        ], body=True),
                    ],md=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                            dbc.Label('병용처방항목 필터링'),
                            dcc.Dropdown(id = 'filter-freq-elements',
                                options = [{'label' :  str(a)+' : '+str(b), 'value' : str(a)} for a, b in zip(atc_list[0], atc_list[1])],
                                placeholder = '필터링할 성분 선택', disabled = True, multi = True, value = 'all'
                            )
                            ])
                        ],style={'margin-bottom':'10px'}),
                        dbc.Card([
                            dbc.CardBody([
                        dt.DataTable(id = 'datatable-paging-freq',
                            columns=[
                                    {'name': i, 'id': i, 'deletable': True} for i in sorted(df_freq.columns) if i!='total_set'
                                ],
                            page_current = 0,
                            page_size = PAGE_SIZE,
                            page_action = 'custom',
                            export_format='csv',
                            sort_action='custom',
                            sort_mode='multi',
                            filter_action='custom',
                            filter_query='',
                            sort_by=[],
                            style_table={'minWidth': '100%'})
                            ])
                        ])
                    ],md=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                            dbc.Label('병용처방항목 필터링'),
                            dcc.Dropdown(id = 'filter-asso-elements',
                                options = [{'label' :  str(a)+' : '+str(b), 'value' : str(a)} for a, b in zip(atc_list[0], atc_list[1])],
                                placeholder = '필터링할 성분 선택', disabled = True, multi = True, value = 'all'
                            )
                            ])
                        ],style={'margin-bottom':'10px'}),
                        dbc.Card([
                            dbc.CardBody([
                        dt.DataTable(id = 'datatable-paging-asso',
                            columns=[
                                    {'name': i, 'id': i, 'deletable': True} for i in sorted(df_asso.columns) if i!='total_set'
                                ],
                            page_current = 0,
                            page_size = PAGE_SIZE,
                            page_action = 'custom',
                            export_format='csv',
                            sort_action='custom',
                            sort_mode='multi',
                            filter_action='custom',
                            filter_query='',
                            sort_by=[],
                            style_table={'minWidth': '100%'})
                            ])
                        ])
                    ],md=5)
                ]
            )
        ],
        style={"margin":"auto"}
    )
                
    init_callback(app, atc_list)
    return app

operators = [['ge ', '>='],
             ['le ', '<='],
             ['lt ', '<'],
             ['gt ', '>'],
             ['ne ', '!='],
             ['eq ', '='],
             ['contains '],
             ['datestartswith ']]

def split_filter_part(filter_part):
    for operator_type in operators:
        for operator in operator_type:
            if operator in filter_part:
                name_part, value_part = filter_part.split(operator, 1)
                name = name_part[name_part.find('{') + 1: name_part.rfind('}')]

                value_part = value_part.strip()
                v0 = value_part[0]
                if (v0 == value_part[-1] and v0 in ("'", '"', '`')):
                    value = value_part[1: -1].replace('\\' + v0, v0)
                else:
                    try:
                        value = float(value_part)
                    except ValueError:
                        value = value_part

                return name, operator_type[0].strip(), value

    return [None] * 3

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
        [Output('datatable-paging-freq', 'columns'), Output('datatable-paging-freq', 'page_count'),Output('datatable-paging-asso', 'columns'), Output('datatable-paging-asso', 'page_count'),
        Output('filter-freq-elements','disabled'),Output('filter-asso-elements','disabled'),Output('alert-msg','children')], 
        [Input('submit_button', 'n_clicks')],
        [State('elements', 'value'), State('select2', 'value'),
        State('num', 'value')]
    )
    def update_table(n_clicks, element, mode, num) :
        print('update')
        t0 = time.time()
        result = []
        if num != None : 
            result = make_table('medicodeset', element, mode, num) + [True,True]
        else : 
            result = make_table(None, element, mode, num) + [False,False]
        t1 = time.time()
        exec_time = t1 - t0
        alert_msg = f"Processing done. Total time: {exec_time}"
        alert = dbc.Alert(alert_msg, color="success", dismissable=True)
        return result + [alert]

    @app.callback(
        [Output('datatable-paging-freq', 'data')],
        [Input('submit_button', 'n_clicks'), Input('datatable-paging-freq', "page_current"),
        Input('datatable-paging-freq', "page_size"),
        Input('datatable-paging-freq','sort_by'),
        Input('datatable-paging-freq', 'filter_query'),
        Input('filter-freq-elements', 'value')]
    )
    def update_paging(n_clicks, page_current, page_size,sort_by,filter,filter_elements) :
        global df_freq
        filtering_expressions = filter.split(' && ')
        if filter_elements!='all':
            filtered_freq=[]
            filtered_freq.append([df_freq[df_freq['total_set'].astype(str).str.contains(ele)].index for ele in filter_elements])
            filtered_freq=[y for x in filtered_freq for y in x]
            dff=df_freq[df_freq.index.isin(filtered_freq)]
        else:
            dff=df_freq
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)
            if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == 'contains':
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == 'datestartswith':
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]
        if len(sort_by):
            dff = dff.sort_values(
            [col['column_id'] for col in sort_by],
            ascending=[
                col['direction'] == 'asc'
                for col in sort_by
            ],
            inplace=False
        )
        page=page_current
        size=page_size
        return dff.iloc[
        page*size : (page + 1) * size, np.r_[:4]
        ].to_dict('records') ,

    @app.callback(
        [Output('datatable-paging-asso', 'data')],
        [Input('submit_button', 'n_clicks'), Input('datatable-paging-asso', "page_current"),
        Input('datatable-paging-asso', "page_size"),
        Input('datatable-paging-asso','sort_by'),
        Input('datatable-paging-asso', 'filter_query'),
        Input('filter-asso-elements', 'value')]
    )
    def update_paging(n_clicks, page_current, page_size,sort_by,filter,filter_elements) :
        global df_asso
        filtering_expressions = filter.split(' && ')
        if filter_elements!='all':
            filtered_rules=[]
            filtered_rules.append([df_asso[df_asso['total_set'].astype(str).str.contains(ele)].index for ele in filter_elements])
            filtered_rules=[y for x in filtered_rules for y in x]
            dff=df_asso[df_asso.index.isin(filtered_rules)]
        else:
            dff=df_asso
        #dff=df_asso
        for filter_part in filtering_expressions:
            col_name, operator, filter_value = split_filter_part(filter_part)
            if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
                dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
            elif operator == 'contains':
                dff = dff.loc[dff[col_name].str.contains(filter_value)]
            elif operator == 'datestartswith':
                dff = dff.loc[dff[col_name].str.startswith(filter_value)]
        if len(sort_by):
            dff = dff.sort_values(
            [col['column_id'] for col in sort_by],
            ascending=[
                col['direction'] == 'asc'
                for col in sort_by
            ],
            inplace=False
        )
        page=page_current
        size=page_size
        return dff.iloc[
        page*size : (page + 1) * size, np.r_[:5]
        ].to_dict('records')


    # @app.callback(
    #     [Output('datatable-paging-freq', 'data'),Output('datatable-paging-freq', 'page_size'),Output('datatable-paging-freq', 'current_page')],
    #     [Input('filter-freq-elements', 'value')],
    # )
    
    # def update_filter_freq_elements(value):
    #     filtered_freq=[]
    #     filtered_freq.append([df_freq[df_freq['total_set'].astype(str).str.contains(ele)].index for ele in value])
    #     filtered_freq=[y for x in filtered_freq for y in x]
    #     dff=df_freq[df_freq.index.isin(filtered_freq)]
    #     return dff.iloc[
    #     0 : 1 * PAGE_SIZE, np.r_[:5]
    #     ].to_dict('records') , len(dff)//PAGE_SIZE + 1, 0

    # @app.callback(
    #     [Output('datatable-paging-asso', 'data'),Output('datatable-paging-asso', 'page_size'),Output('datatable-paging-asso', 'current_page')],
    #     [Input('filter-asso-elements', 'value')],
    # )
    # def update_filter_asso_elements(value):
    #     filtered_asso=[]
    #     filtered_asso.append([df_asso[df_asso['total_set'].astype(str).str.contains(ele)].index for ele in value])
    #     filtered_asso=[y for x in filtered_asso for y in x]
    #     dff=df_asso[df_asso.index.isin(filtered_asso)]
    #     return dff.iloc[
    #     0 : 1 * PAGE_SIZE, np.r_[:5]
    #     ].to_dict('records') , len(dff)//PAGE_SIZE + 1, 0