import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_table
import pandas as pd
from pymongo import MongoClient
from bson.son import SON
import time


host = 'localhost'
port = 27017
database = 'dwDB'
client = MongoClient(host = host, port = port)
db = client[database]
collection = db.get_collection('db1')

#aggregate
start2 = time.time()
pipelines = list()
temp = list()
pipelines.append({'$match' : {'약품일반성분명코드' : '142303ATB'}})
temp.append({'$match' : {'약품일반성분명코드' : '142303ATB'}})
pipelines.append({'$group' : {'_id' : '$가입자일련번호', '방문횟수' : {'$sum' : 1}}})
result = db.db1.aggregate(pipelines)
df2 = pd.DataFrame()
for doc in result :
    if doc['방문횟수'] > 2 :
        b = doc['_id']
        temp.append({'$match' : {'가입자일련번호' : b}})
        c = db.collection.aggregate(temp)
        df2 = pd.DataFrame(list(c))
        break
#df2 = pd.DataFrame(list(result))
print(time.time() - start2)
print(df2)
print("grouping")


# df = pd.DataFrame(list(cursor))
# print(df[0:5])

app = dash.Dash(__name__)

PAGE_SIZE = 5
app.layout = html.Div([
    html.Div(id = 'title', children = 'example')
])
# app.layout = dash_table.DataTable(
#     id='datatable-paging',
#     columns=[
#         {"name": i, "id": i} for i in sorted(df.columns[2:])
#     ],
#     page_current=0,
#     page_size=PAGE_SIZE,
#     page_action='custom'
# )
#
#
# @app.callback(
#     Output('datatable-paging', 'data'),
#     [Input('datatable-paging', "page_current"),
#      Input('datatable-paging', "page_size")])
# def update_table(page_current,page_size):
#     return df.iloc[
#         page_current*page_size : (page_current + 1) * page_size, 2:
#     ].to_dict('records')


if __name__ == '__main__':
    app.run_server(debug=True)
