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
global result_json

def make_df(value) :
    
    start = time.time()
    collection = make_client('db1')
    cursor = collection.find({"약품일반성분명코드" : value})
    #df = pd.DataFrame.from_dict((collection.find({"약품일반성분명코드" : value})))
    #df = pd.DataFrame.from_records((collection.find({"약품일반성분명코드" : value})))
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
    global result_json
    if value != None :
        df = make_df(value)
    else : 
        df = pd.DataFrame()
    result_json = df.to_json(orient='split')
    #res = requests.post("http://127.0.0.1:8080/dashboard1/download_csv", data=result_json)
    #flask.session['result_json'] = result_json
    return [[{"name" : i, "id" : i} for i in df.columns], result_json, len(df)//PAGE_SIZE + 1]

def make_graph(df, value) :
    if value != None :
        print("graph")
        # fig = display_1(df2)
        # hist_data = [df['복약순응도'].astype('int64')]
        # group_labels = ['복약순응도']
        # fig = ff.create_distplot(hist_data, group_labels)
        #fig = go.Figure(data=[go.Histogram(x=x)])
        x = df['복약순응도']
        fig = px.histogram(df, x=x, histnorm = "probability density")
        return dcc.Graph(figure = fig)
    else :
        return dcc.Graph()

def create_dashboard1(server) : 
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard1/', external_stylesheets=external_stylesheets)
    
    app.layout = html.Div([
        html.Div(id = 'title', children = '복약순응도'),
        html.Div(dcc.Input(id = 'code_input', type = 'text')),
        # html.Div(id = 'elements', children = [
        #     dcc.Dropdown(id = 'elements',
        #             options=[
        #                 {'label' : a+' : '+b, 'value' : a} for a, b in zip(atc_list[0], atc_list[1])],
        #                 placeholder = '원하는 성분 선택', multi = True, value = None, style = {'width' : '35%'})]),
        html.Button('Submit', id = 'submit_button', n_clicks = 0),
        html.Div(id = 'result', children='결과'),
        html.Div(id = 'table', children = [
            html.A(html.Button('다운로드', id = 'download_button', n_clicks = 0), id = 'csv_link', href="/dashboard1/download_csv"),
            dt.DataTable(id = 'datatable-paging',
            page_current = 0, page_size = PAGE_SIZE,
            page_action = 'custom')], style = {'display' : 'inline'}),
        html.Br(),
        html.Div(children = '그래프'),
        html.Div(id = 'graph', style = {'display' : 'none'}),
        html.Div(id = 'intermediate', style = {'display' : 'none'})
        # html.Div(id = 'download', children = [html.A(html.Button('다운로드', id = 'download_button', n_clicks = 0), id = 'csv_link', href = '/dash/urlToDownload')])
    ])
    init_callback(app)
    return app

def init_callback(app) : 

    @app.callback(
        [Output('datatable-paging', 'columns'), Output('intermediate', 'children'),
        Output('datatable-paging', 'page_count'), Output('table', 'style'), Output('graph', 'style')],
        [Input('submit_button', 'n_clicks')],
        [State('code_input', 'value')]
    )
    def update_table(n_clicks, value):
        print("update_Table")
        if value == None :
            return make_table(value) + [{'display' : 'inline'}, {'display' : 'none'}]
        else :
            return make_table(value) + [{'display' : 'block'}, {'display' : 'inline'}]

    @app.callback(
        Output('datatable-paging', 'data'),
        [Input('datatable-paging', "page_current"),
        Input('datatable-paging', "page_size"),
        Input('intermediate', 'children')]
    )
    def update_paging(page_current, page_size, data) :
        print('paging {} {}'.format(page_current, page_size))
        df = pd.DataFrame()
        if data != None : 
            df = pd.read_json(data, orient='split')
        return df.iloc[
            page_current*page_size : (page_current + 1) * page_size
        ].to_dict('records')

    @app.callback(
        Output('graph', 'children'),
        [Input('submit_button', 'n_clicks'), Input('intermediate', 'children')],
        [State('code_input', 'value')]
    )
    def update_graph(n_clicks, data, value) :
        print('graph {} {}'.format(n_clicks, value))
        if data != None :
            df = pd.read_json(data, orient='split')
            return make_graph(df, value)
        else :
            df = pd.DataFrame()
            return make_graph(df, None)
    
    @app.server.route('/dashboard1/download_csv')
    def download_csv() :
        output_stream = StringIO()
        output_stream.write(u'\ufeff')
        # dict = [
        #          {'이름' : 'hyejung', '나이' : 10, '주소' : '수원시'},
        #          {'이름' : 'moon', '나이' : 12, '주소' : '서울시'}
        # ]
        # df = pd.DataFrame(dict).set_index("이름")
        global result_json
        df = pd.read_json(result_json, orient='split')
        df = df.set_index("순번")
        print("dataframe ready")
        start = time.time()
        df.to_csv(output_stream)
        print(time.time()-start)
        print("csv ready")
        response = flask.Response(
            output_stream.getvalue(),
            mimetype='text/csv',
            content_type='application/octet-stream',
        )
        response.headers["Content-Disposition"] = "attachment; filename=post_export.csv"
        return response

    # @app.callback(
    #     Output('csv_link', 'href'),
    #     [Input('code_input', 'value')]
    # )
    # def update_link(value) :
    #     print("click")
    #     return '/dash/urlToDownload?value={}'.format(value)

    # @app.server.route('/dash/urlToDownload')
    # def download_csv() :
    #     value = flask.request.args.get('value')
    #     print("download")
    #     str_io = io.StringIO()
    #     dict = [
    #         {'name' : 'hello', 'age' : 10},
    #         {'name' : 'world', 'age' : 12}
    #     ]
    #     testcsv = pd.DataFrame(dict).reset_index(drop=True)
    #     #testcsv = df[:15]
    #     testcsv.to_csv(str_io)
    #     mem = io.BytesIO()
    #     mem.write(str_io.getvalue().encode('utf-8'))
    #     mem.seek(0)
    #     str_io.close()
    #     return flask.send_file(mem,
    #      mimetype = 'text/csv',
    #      attachment_filename = 'downloadFile.csv',
    #      as_attachment = True)





# if __name__ == '__main__':
#     app = create_dashboard1()
#     app.run_server(debug=True)
