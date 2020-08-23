import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output, State
import yaml
from pymongo import MongoClient
import pandas as pd
from functions import Visit_count, Calculate, Date_Number, Medication

# with open(r'C:\Users\Ower\Desktop\project1\config.yaml', 'r') as ymlfile:
#     cfg = yaml.load(ymlfile, Loader=yaml.BaseLoader)

host = 'localhost'
port = 27017
database = 'dwDB'
client = MongoClient(host = host, port = port)
db = client[database]
collection = db.get_collection('db1')

print("start")
pipeline = [
    {"$match" : {"약품일반성분명코드" : "233102ATB"}},
    {"$group" : {"_id" : "$가입자일련번호", "count" : {"$sum" : 1}}},
    {"$out" : "count_db"}]
cursor1 = collection.aggregate(pipeline = pipeline)
print("end")

# print("pipe2")
# pipeline2 = [
#     {"$match" : {"약품일반성분명코드" : "233102ATB"}},
#     {"$lookup" : {"from" : "count_db", "localField" : "_id", "foreignField": "가입자일련번호", "as": "방문횟수"}},
#     {"$match" : {"방문횟수" : {"$gt" : 2}}},
#     {"$sort" :  {"가입자일련번호" : 1, "요양개시일자" : 1}}]

# cursor2 = collection.aggregate(pipeline = pipeline2)
# print("pipe2 end")
# a = list(cursor2)
# print(a[:3])

# cursor = db.db1.find({"약품일반성분명코드" : "142303ATB"})
# #df2 = pd.DataFrame.from_records(cursor)
# df = pd.DataFrame(list(cursor))
# df.drop('_id', axis = 1, inplace = True)
# df[' index'] = range(1, len(df) + 1)
#
# df['요양개시일자'] = pd.to_datetime(df['요양개시일자'].astype(str))
# df = Visit_count(df)
# df = Calculate(df)
# df = Date_Number(df)
# df2 = Medication(df)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
def make_df(value) :
    cursor = db.db1.find({"약품일반성분명코드" : value})
    
    print("read done")
    #df2 = pd.DataFrame.from_records(cursor)
    df = pd.DataFrame(list(cursor))
    if value != "" :
        df.drop('_id', axis = 1, inplace = True)
        df[' index'] = range(1, len(df) + 1)

        df['요양개시일자'] = pd.to_datetime(df['요양개시일자'].astype(str))
        df = Visit_count(df)
        print("visit count done")
        df = Calculate(df)
        print("calculate done")
        df = Date_Number(df)
        print("date number done")
        df2 = Medication(df)
        print("medication done")
    return df2

df2 = pd.DataFrame()
#code = "142303ATB"
def make_table(value) :
    print(value)
    global df2
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

PAGE_SIZE = 15
app.layout = html.Div([
    html.Div(id = 'title', children = '복약순응도'),
    html.Div(dcc.Input(id = 'code_input', type = 'text')),
    html.Button('Submit', id = 'submit-button', n_clicks = 0),
    html.Div(id = 'result', children='결과'),
    html.Div(id = 'table', children = make_table(None), style = {'marginBottom' : 200}),
    html.Br(),
    html.Div(children='그래프') #style = {'display' : 'none'})
])

@app.callback(
    Output('table', 'children'),
    [Input('submit-button', 'n_clicks')],
    [State('code_input', 'value')]
)
def update_output(n_clicks, value):
    return make_table(value)


@app.callback(
    Output('datatable-paging', 'data'),
    [Input('datatable-paging', "page_current"),
    Input('datatable-paging', "page_size")]
)
def update_table(page_current, page_size) :
    global df2
    return df2.iloc[
        page_current*page_size : (page_current + 1) * page_size
    ].to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=True)