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
    global df_asso, df_freq
    if table == None :
        df_freq = pd.DataFrame()
        df_asso = pd.DataFrame()
    else : df_freq, df_asso = functions2.calculate(table, element, mode, num)
    return [[{"name" : i, "id" : i} for i in df_freq.columns if i != 'total_set'], len(df_freq)//PAGE_SIZE + 1, [{"name" : i, "id" : i} for i in df_asso.columns if i != 'total_set'], len(df_asso)//PAGE_SIZE + 1]
      

def create_dashboard2(server) :
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard2/', external_stylesheets=external_stylesheets)
    selected = []
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
                    options = [{'label' :  str(a)+' : '+str(b), 'value' : str(a)} for a, b in zip(atc_list[0], atc_list[1])],
                    placeholder = '원하는 성분 선택', disabled = True, multi = True, value = None
                )]),
            html.Div(id = 'result', children = [
                html.Div(children = '지지도 입력'),
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
            ]),
            dbc.Button("조회",id="submit_button", n_clicks=0, color="primary", block=True)
            #html.Button('Submit', id = 'submit_button', n_clicks = 0, style={'display':'inline'})
        ],style={'width':'35%','display':'inline-block'}),
         
        html.Br(),
        dcc.Loading(
            id="loading-table",
            type="default",
            children=[html.Div(id='table_frame',
            children=[
                html.Div(id = 'table_freq',
                children=[
                html.H1(id = 'table_freq_title', children = '상위 빈도 수',style={'textAlign': 'center'}),
                dt.DataTable(id = 'datatable-paging-freq',
                columns=[
                        {'name': i, 'id': i, 'deletable': True} for i in sorted(df_freq.columns) if i != 'total_set'
                    ],
                    page_current = 0,
                    page_size = PAGE_SIZE,
                    page_action = 'custom',
                    export_format='csv',
                    sort_action='custom',
                    sort_mode='multi',
                    filter_action='custom',
                    filter_query='',
                    sort_by=[])],
                style = {'display' : 'inline-block','width':'45%'}),
                html.Div(id = 'table_asso',
                children=[
                html.H1(id = 'table_asso_title', children = '병용처방약품 연관성 분석',style={'textAlign': 'center'}),
                dt.DataTable(id = 'datatable-paging-asso',
                columns=[
                        {'name': i, 'id': i, 'deletable': True} for i in sorted(df_asso.columns) if i != 'total_set'
                    ],
                    page_current = 0,
                    page_size = PAGE_SIZE,
                    page_action = 'custom',
                    export_format='csv',
                    sort_action='custom',
                    sort_mode='multi',
                    filter_action='custom',
                    filter_query='',
                    sort_by=[])
                    ],
                style = {'display' : 'inline-block','width':'45%','margin-left':'10%'})
            ],
            style = {'display' : 'none', 'margin-top':'5%'})]
        ),
        # html.Div(id = 'intermediate_atc', style = {'display' : 'none'}),
        # html.Div(id = 'intermediate_freq', style = {'display' : 'none'}),
        # html.Div(id = 'intermediate_asso', style = {'display' : 'none'})
    ])
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

                # word operators need spaces after them in the filter string,
                # but we don't want these later
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
        [Output('datatable-paging-freq', 'columns'), Output('datatable-paging-freq', 'page_count'),Output('datatable-paging-asso', 'columns'), Output('datatable-paging-asso', 'page_count'), Output('table_frame', 'style')], 
        [Input('submit_button', 'n_clicks')],
        [State('elements', 'value'), State('select2', 'value'),
        State('num', 'value')]
    )
    def update_table(n_clicks, element, mode, num) :
        print('update')
        result = []
        if num != None : 
            result = make_table('medicodeset', element, mode, num) + [{'display' : 'inline'}]
        else : 
            result = make_table(None, element, mode, num) + [{'display' : 'none'}]
        return result

    @app.callback(
        Output('datatable-paging-freq', 'data'),
        [Input('submit_button', 'n_clicks'), Input('datatable-paging-freq', "page_current"),
        Input('datatable-paging-freq', "page_size"),
        Input('datatable-paging-freq','sort_by'),
        Input('datatable-paging-freq', 'filter_query')]
    )
    def update_paging(n_clicks, page_current, page_size,sort_by,filter) :
        filtering_expressions = filter.split(' && ')
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
        page*size : (page + 1) * size
        ].to_dict('records')
    # @app.callback(
    #     Output('datatable-paging-asso', 'data'),
    #     [Input('submit_button', 'n_clicks'), Input('datatable-paging-asso', "page_current"),
    #     Input('datatable-paging-asso', "page_size")]
    # )
    # def update_paging(n_clicks, page_current, page_size) :
    #     return df_asso.iloc[
    #         page_current*page_size : (page_current + 1) * page_size
    #     ].to_dict('records')

    @app.callback(
        Output('datatable-paging-asso', 'data'),
        [Input('submit_button', 'n_clicks'), Input('datatable-paging-asso', "page_current"),
        Input('datatable-paging-asso', "page_size"),
        Input('datatable-paging-asso','sort_by'),
        Input('datatable-paging-asso', 'filter_query')]
    )
    def update_paging(n_clicks, page_current, page_size,sort_by,filter) :
        filtering_expressions = filter.split(' && ')
        dff=df_asso
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
        page*size : (page + 1) * size
        ].to_dict('records')
