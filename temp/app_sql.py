import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State
import pymysql
import pandas as pd
from functions import Visit_count, Calculate, Date_Number, Medication
import time
import numpy as np
import plotly.figure_factory as ff

HOST_NAME = '127.0.0.1'
PORT_NUMBER = 3306
USER_NAME = "root"
PASSWORD = "GW1997GW"
DATATBASE_NAME = "daewoong"
db = pymysql.connect(
    host = HOST_NAME,
    port = PORT_NUMBER,
    user = USER_NAME,
    passwd = PASSWORD,
    db = DATATBASE_NAME,
    charset = 'utf8'
)

SQL = "SELECT * FROM example"

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def make_df(value) :

    # 요양 개시 일자 DATETME으로 바꾸는 것도 여기서 가능할 수도...
    start = time.time()
    #df = pd.DataFrame.from_dict((collection.find({"약품일반성분명코드" : value})))
    df2 = pd.read_sql_query(SQL, db)
    print(time.time() - start)
    print("read done")
    df2[' index'] = range(1, len(df2) + 1)

    # df['date'] = pd.to_datetime(df['date'].astype(str))
    # start2 = time.time()
    # df = Visit_count(df)
    # print(time.time() - start2)
    # print("visit count done")
    # df = Calculate(df)
    # print("calculate done")
    # df = Date_Number(df)
    # print("date number done")
    # df2 = Medication(df)
    # print("medication done")
    return df2

df2 = pd.DataFrame()
def make_table(value):
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
