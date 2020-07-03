from flask import Flask
import dash
import dash_bootstrap_components as dbc

import json
import networkx as nx

server = Flask(__name__) # we pass this server to gunicorn for deployment

app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])
