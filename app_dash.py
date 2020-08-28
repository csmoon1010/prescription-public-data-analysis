import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from functions import Visit_count, Calculate, Date_Number, Medication, Statistics
from connect_mongo import make_client
import time
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import flask
from io import StringIO
import requests
import math
#pd.options.mode.chained_assignment=None
PAGE_SIZE = 10
result_df = pd.DataFrame()
s_df = pd.DataFrame()

def get_atc() :
    atc_df=pd.read_csv('code_list.csv',encoding='utf-8')
    #atc = make_client('atc')
    #atc_df = pd.DataFrame.from_dict(atc.find())
    atc_code = atc_df['주성분코드'].to_list()
    atc_spec = atc_df['Spec'].to_list()
    return [atc_code, atc_spec]

## dataframe setting ##
def clear_df() :
    global result_df
    result_df = pd.DataFrame()

## make 함수 ##
def make_df(value) :
    print(value)
    if(len(value)==1):
        start = time.time()
        collection_medi = make_client('medicine')
        cursor = collection_medi.find({"약품일반성분명코드" : value[0]})
    else:     
        start = time.time()
        collection_medicode = make_client('medicodeset')
        collection_medi = make_client('medicine')
        cursor_medicode=collection_medicode.aggregate(pipeline=[
        {
            "$match" : {
            "medicode":{
                "$all": value
                }
            }
        },
        ], allowDiskUse=True
        )
        pres_code=pd.DataFrame.from_dict(cursor_medicode)
        if(len(pres_code)==0):
            print("--------------------------------")
            return pd.DataFrame([])
        pres_code=pres_code['_id'].to_list()
        print(pres_code[:5])
        cursor=collection_medi.aggregate(pipeline=[
        {
            "$match" : {
                "처방내역일련번호" : {
                    "$in" : pres_code
                }
            }
        },
        {
            "$match" : {
                "약품일반성분명코드" : {
                    "$in" : value
                }
            }
        }
        ], allowDiskUse=True
        )
    df = pd.DataFrame.from_dict(cursor)
    print(time.time() - start)
    print("read done")
    df.drop('_id', axis = 1, inplace = True)
    df['요양개시일자'] = pd.to_datetime(df['요양개시일자'].astype(str))
    
    df = Visit_count(df)
    print("visit count done")
    df = Calculate(df)
    print("calculate done")
    df = Date_Number(df)
    print("date number done")
    df = Medication(df)
    print("medication done")
    df['요양개시일자'] = df['요양개시일자'].astype(str)
    return df

def make_table(value) :
    #global result_json
    global result_df
    print('make_table {}'.format(result_df.shape[0]))
    if value != None :
        result_df = make_df(value)
    else : 
        result_df = pd.DataFrame()
    #result_json = df.to_json(orient='split')
    total_page = math.ceil(len(result_df)/PAGE_SIZE)
    data_size = len(result_df)
    return [[{"name" : i, "id" : i} for i in result_df.columns], total_page, ['데이터 개수 : {}'.format(data_size)]]

def calc_statistics(value) :
    global result_df
    global s_df
    if value != None :
        s_df = Statistics(result_df)
    else :
        s_df = pd.DataFrame()
    return [s_df.to_dict('records'), [{"name" : i, "id" : i} for i in s_df.columns]]

def make_graph(value) :
    if value != None :
        print("graph")
        x = result_df['복약순응도']
        fig = px.histogram(result_df, x=x, histnorm = "probability density")
        return dcc.Graph(figure = fig)
    else :
        return dcc.Graph()

def create_dashboard1(server) :
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard1/', external_stylesheets=external_stylesheets)
    atc_list = get_atc()
    app.layout = html.Div(className = 'total-container', children = [
        html.Div(className = 'header',
            children = [
                html.H3(className = 'title', children = '복약순응도')
            ]
        ),
        html.Div(id = 'input-container', children = [
                html.Div(id = 'input-title', className='search', children= '약품일반성분명코드'),
                html.Div(id = 'input-dropdown', className='search', children= [dcc.Dropdown(id = 'code_input',
                     options=[
                         {'label' : str(a) + ' : ' + str(b), 'value' : str(a)} for a, b in zip(atc_list[0], atc_list[1])],
                         placeholder = '원하는 성분 선택',multi = True,
                        value = None
                    )]
                ),
                html.Button(id = 'submit_button', className='search', children='검색', n_clicks = 0)]),
        dcc.Loading(
            id="loading-table",
            type="default",
            children=html.Div(className='wrapper', children = [
            html.Div(className='item',
                children = [html.Div(id = 'table', children=[
                    html.Div(id='download-button', children=[html.A(html.Button('다운로드', n_clicks = 0), id = 'csv_link', href="/dashboard1/download_csv"),
                   html.Span(id='data_len', className = 'size_explain')]),
                    dt.DataTable(id = 'datatable-statistics',
                    columns=[
                        {'name': i, 'id': i, 'deletable': True} for i in sorted(s_df.columns)
                    ],
                    style_as_list_view=True,
                    style_cell={'padding' : '5px'},
                    style_header={'backgroundColor' : 'white', 'fontWeight' : 'bold'}),
                    dt.DataTable(id = 'datatable-paging',
                    columns=[
                        {'name': i, 'id': i, 'deletable': True} for i in sorted(result_df.columns)
                    ],
                    page_current = 0,
                    page_size = PAGE_SIZE,
                    page_action = 'custom',
                    sort_action='custom',
                    sort_mode='multi',
                    filter_action='custom',
                    filter_query='',
                    sort_by=[])
                    ],
            style = {'display' : 'none'})]),
            html.Div(className='item', children = [html.Div(id = 'graph', style = {'display' : 'none'})])            
        ])
        ),      
    ])
    init_callback(app)
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

def init_callback(app) : 
    @app.callback(
        [Output('datatable-paging', 'columns'),Output('datatable-paging', 'page_count'), Output('data_len', 'children'),
        Output('table', 'style'), Output('graph', 'style')],
        [Input('submit_button', 'n_clicks')],
        [State('code_input', 'value')]
    )
    def update_table(n_clicks, value):
        print("update_Table")
        if value == None :
            return make_table(value) + [{'display' : 'none'}, {'display' : 'none'}]
        else :
            return make_table(value) + [{'display' : 'block'}, {'display' : 'block'}]

    @app.callback(
        Output('datatable-paging', 'data'),
        [Input('submit_button', 'n_clicks'), Input('datatable-paging', "page_current"),
        Input('datatable-paging', "page_size"),
        Input('datatable-paging','sort_by'),
        Input('datatable-paging', 'filter_query'),
        Input('datatable-paging', 'page_count')]
    )
    def update_paging(n_clicks, page_current, page_size,sort_by,filter, page_count) :
        filtering_expressions = filter.split(' && ')
        dff=result_df
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

    @app.callback(
        [Output('datatable-statistics', 'data'),Output('datatable-statistics', 'columns')],
        [Input('submit_button', 'n_clicks'), Input('datatable-paging', 'page_count')],
        [State('code_input', 'value')]
    )
    def update_statistics(n_clicks, columns, value) :
        return calc_statistics(value)

    @app.callback(
        Output('graph', 'children'),
        [Input('submit_button', 'n_clicks'), Input('datatable-paging', 'page_count')],
        [State('code_input', 'value')]
    )
    def update_graph(n_clicks, page_count, value) :
        print('graph {} {}'.format(n_clicks, value))
        return make_graph(value)

    @app.server.route('/dashboard1/download_csv')
    def download_csv() :
        start = time.time()
        output_stream = StringIO()
        output_stream.write(u'\ufeff')
        #global result_json
        #df = pd.read_json(result_json, orient='split')
        global result_df
        result_df = result_df.set_index("순번")
        print(time.time()-start)
        print("dataframe ready")
        start = time.time()
        result_df.to_csv(output_stream)
        print(time.time()-start)
        print("csv ready")
        response = flask.Response(
            output_stream.getvalue(),
            mimetype='text/csv',
            content_type='application/octet-stream',
        )
        response.headers["Content-Disposition"] = "attachment; filename=post_export.csv"
        return response