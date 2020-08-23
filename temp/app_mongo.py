import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
import pandas as pd
from functions import Visit_count, Calculate, Date_Number, Medication
import time
import numpy as np
import plotly.figure_factory as ff
from sshtunnel import SSHTunnelForwarder
from bson.json_util import loads, dumps

# with open(r'C:\Users\Ower\Desktop\project1\config.yaml', 'r') as ymlfile:
#     cfg = yaml.load(ymlfile, Loader=yaml.BaseLoader)

MONGO_HOST = "210.117.182.242"
MONGO_PORT = 27017
MONGO_DB = "daewoong"
MONGO_USER = "dblab"
MONGO_PASS = "dbl5511!@"
server = SSHTunnelForwarder(
    MONGO_HOST,
    ssh_username=MONGO_USER,
    ssh_password=MONGO_PASS,
    remote_bind_address=('127.0.0.1', 27017)
)

server.start()

client = MongoClient('127.0.0.1', server.local_bind_port,serverSelectionTimeoutMS=200000)
db = client[MONGO_DB]
collection = db.get_collection('medicine')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
# def iterator2dataframes(iterator, chunk_size: int):
#   """Turn an iterator into multiple small pandas.DataFrame
#
#   This is a balance between memory and efficiency
#   """
#   records = []
#   frames = []
#   for i, record in enumerate(iterator):
#       records.append(record)
#       if i % chunk_size == chunk_size - 1:
#           frames.append(pd.DataFrame(records))
#           records = []
#   if records :
#       print(records)
#       frames.append(pd.DataFrame(records))
#   return pd.concat(frames)

# def iterator2dataframes(iterator, chunk_size: int):
#   """Turn an iterator into multiple small pandas.DataFrame

#   This is a balance between memory and efficiency
#   """
#   records = []
#   frames = []
#   for i, record in enumerate(iterator):
#       records.append(record)
#       if i % chunk_size == chunk_size - 1:
#           frames.append(pd.DataFrame(records))
#           records = []
#   if records :
#       print(records)
#       frames.append(pd.DataFrame(records))
#   return pd.concat(frames)

def make_df(value) :
    #df = pd.DataFrame.from_records(cursor)
    #df = pd.DataFrame(list(cursor))

    # 요양 개시 일자 DATETME으로 바꾸는 것도 여기서 가능할 수도...
    #df = iterator2dataframes(cursor, 1000)
    start = time.time()
    cursor = collection.find({"약품일반성분명코드" : value})
    a = dumps(cursor)
    print(time.time() - start)
    df = pd.DataFrame.from_dict(cursor)
    print("read done")
    df.drop('_id', axis = 1, inplace = True)
    df[' index'] = range(1, len(df) + 1)

    df['요양개시일자'] = pd.to_datetime(df['요양개시일자'].astype(str))
    
    return df2

df2 = pd.DataFrame()
#code = "142303ATB"
def make_table(value) :
    global df2
    global show
    if value != None :
        df2 = make_df(value)
    return dt.DataTable(
        id = 'datatable-paging',
        columns = [
            {"name" : i, "id" : i} for i in sorted(df2.columns)
        ],
        page_current = 0,
        page_size = PAGE_SIZE,
        page_action = 'custom'
    )

PAGE_SIZE = 10
app.layout = html.Div([
    html.Div(id = 'title', children = '복약순응도'),
    html.Div(dcc.Input(id = 'code_input', type = 'text')),
    html.Button('Submit', id = 'submit-button', n_clicks = 0),
    html.Div(id = 'result', children='결과'),
    html.Div(id = 'table', children = make_table(None), style = {'display' : 'none'})
])

@app.callback(
    [Output('table', 'children'), Output('table', 'style')],
    [Input('submit-button', 'n_clicks')],
    [State('code_input', 'value')]
)
def update_table(n_clicks, value):
    if value == None :
        return [make_table(value), {'display' : 'None'}]
    else :
        return [make_table(value), {'display' : 'block'}]

@app.callback(
    Output('datatable-paging', 'data'),
    [Input('datatable-paging', "page_current"),
    Input('datatable-paging', "page_size")]
)
def update_paging(page_current, page_size) :
    global df2
    return df2.iloc[
        page_current*page_size : (page_current + 1) * page_size
    ].to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=True)
