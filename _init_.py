from flask import Flask
import dash

server = Flask(__name__)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
dashboard1 = dash.Dash(__name__, server = server, url_base_pathname = '/dashboard1/', external_stylesheets=external_stylesheets)
