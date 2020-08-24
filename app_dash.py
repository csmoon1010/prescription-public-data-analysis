import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from functions import Visit_count, Calculate, Date_Number, Medication, display_1
from connect_mongo import make_client
import time
import numpy as np
#import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px
from sshtunnel import SSHTunnelForwarder
import flask
from io import StringIO
import requests

PAGE_SIZE = 10
result_df = pd.DataFrame()

def get_atc() :
    atc = make_client('atc')
    atc_df = pd.DataFrame.from_dict(atc.find())
    atc_code = atc_df['주성분코드'].tolist()
    atc_spec = atc_df['Spec'].tolist()
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
    #return [[{"name" : i, "id" : i} for i in df.columns], result_json, len(df)//PAGE_SIZE + 1]
    return [[{"name" : i, "id" : i} for i in result_df.columns], len(result_df)//PAGE_SIZE + 1]
    
def make_graph(value) :
    global result_df
    if value != None :
        print("graph")
        # fig = display_1(df2)
        # hist_data = [df['복약순응도'].astype('int64')]
        # group_labels = ['복약순응도']
        # fig = ff.create_distplot(hist_data, group_labels)
        #fig = go.Figure(data=[go.Histogram(x=x)])
        x = result_df['복약순응도']
        fig = px.histogram(result_df, x=x, histnorm = "probability density")
        return dcc.Graph(figure = fig)
    else :
        return dcc.Graph()

def create_dashboard1(server) :
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard1/', external_stylesheets=external_stylesheets)
    atc_list = get_atc()
    app.layout = html.Div(id = 'total-container', children = [
        html.Div(id = 'header',
            children = [
                html.H4(id = 'title', children = '복약순응도')
            ]
        ),
        html.Div(id = 'input-container', children = [
                html.Div(id = 'input-title', className='search', children= '약품일반성분명코드'),
                html.Div(dcc.Dropdown(id = 'code_input',
                     options=[
                         {'label' : a+' : '+b, 'value' : a} for a, b in zip(atc_list[0], atc_list[1])],
                         placeholder = '원하는 성분 선택',multi = True,
                        value = None,
                        style = {'width' : '80%'}
                        )
                        ),
                html.Button(id = 'submit_button', className='search', children='검색', n_clicks = 0)]),
        dcc.Loading(
            id="loading-table",
            type="default",
            children=html.Div(className='wrapper', children = [
            html.Div(className='item',
                children = [html.Div(id = 'table', children=[
                    #html.Div(id='download-button', children=[html.A(html.Button('다운로드', n_clicks = 0), id = 'csv_link', href="/dashboard1/download_csv")]),
                    dt.DataTable(id = 'datatable-paging',
                    page_current = 0, page_size = PAGE_SIZE,
                    page_action = 'custom',
                    export_format='csv')],style = {'display' : 'none'})]),
            html.Div(className='item', children = [html.Div(id = 'graph', style = {'display' : 'none'})])            
        ])
        ),      
        # html.Div(id = 'intermediate', style = {'display' : 'none'})
        # html.Div(id = 'download', children = [html.A(html.Button('다운로드', id = 'download_button', n_clicks = 0), id = 'csv_link', href = '/dash/urlToDownload')])
    ])
    init_callback(app)
    return app

def init_callback(app) : 
    @app.callback(
        [Output('datatable-paging', 'columns'),Output('datatable-paging', 'page_count'),
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
        Input('datatable-paging', "page_size")]
    )
    def update_paging(n_clicks, page_current, page_size) :
        print('paging {} {}'.format(page_current, page_size))
        # if data != None : 
        #     df = pd.read_json(data, orient='split')
        global result_df
        return result_df.iloc[
            page_current*page_size : (page_current + 1) * page_size
        ].to_dict('records')

    @app.callback(
        Output('graph', 'children'),
        [Input('submit_button', 'n_clicks')],
        [State('code_input', 'value')]
    )
    def update_graph(n_clicks, value) :
        print('graph {} {}'.format(n_clicks, value))
        return make_graph(value)
    
    # @app.server.route('/dashboard1/download_csv')
    # def download_csv() :
    #     start = time.time()
    #     output_stream = StringIO()
    #     output_stream.write(u'\ufeff')
    #     global result_df
    #     result_df = result_df.set_index("순번")
    #     print(time.time()-start)
    #     print("dataframe ready")
    #     start = time.time()
    #     result_df.to_csv(output_stream)
    #     print(time.time()-start)
    #     print("csv ready")
    #     response = flask.Response(
    #         output_stream.getvalue(),
    #         mimetype='text/csv',
    #         content_type='application/octet-stream',
    #     )
    #     response.headers["Content-Disposition"] = "attachment; filename=post_export.csv"
    #     return response
