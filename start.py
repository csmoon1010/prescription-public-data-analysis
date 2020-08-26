from flask import Flask, render_template, request, redirect, Response
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from io import StringIO
import pandas as pd
from app_dash import create_dashboard1, clear_df
from app_dash2 import create_dashboard2

server = Flask(__name__)

@server.route('/')
def reder_start():
    clear_df()
    print("mainpage")
    return render_template('start.html')

@server.route('/dashboard1')
def render_dashboard1():
    return redirect('/drug_compliance')

@server.route('/dashboard2')
def render_dashboard2():
    return redirect('/prescription')

app = DispatcherMiddleware(server, {
    '/drug_compliance' : create_dashboard1(server),
    '/prescription' : create_dashboard2(server)
})

run_simple('127.0.0.1', 8080, app, use_reloader=False, use_debugger=False)
