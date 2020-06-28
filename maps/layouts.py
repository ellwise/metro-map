import dash
import dash_core_components as dcc
import dash_html_components as html

import dash_bootstrap_components as dbc

import networkx as nx
import json
import math

def make_layout():

    return dbc.Container(
        children=[
            dbc.Row(
                className="mt-3",
                children=[
                    dbc.Col(
                        xs=12,
                        sm=12,
                        md=12,
                        lg=12,
                        xl=9,
                        children=dcc.Dropdown(
                            id="maps-dropdown",
                            multi=True,
                            clearable=True,
                            placeholder="Add stops to generate a map...",
                            persistence=True,
                            persistence_type="local"
                        )
                    ),
                    dbc.Col(
                        xs=12,
                        sm=12,
                        md=12,
                        lg=12,
                        xl=3,
                        children=dbc.RadioItems(
                            className="mt-2",
                            options=[
                                {"label": "Schematic", "value": "schematic"},
                                {"label": "Geographical", "value": "geographical"},
                            ],
                            value="schematic",
                            id="maps-radioitems-input",
                            inline=True
                        )
                    ),
                ]
            ),
            dbc.Row(
                className="mt-3",
                children=dbc.Col(
                    children=html.Div(id="maps-plot")
                )
            ),
            dcc.Store(
                id="maps-store",
                storage_type="local"
            )
        ]
    )
