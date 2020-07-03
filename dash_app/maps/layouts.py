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
                justify="between",
                children=[
                    dbc.Col(
                        width="auto",
                        children=dbc.Checklist(
                            options=[
                                {"label":"Bus", "value":"bus"},
                                {"label":"DLR", "value":"dlr"},
                                {"label":"Overground", "value":"overground"},
                                {"label":"Tube", "value":"tube"}
                            ],
                            value=["bus","dlr","overground","tube"],
                            id="maps-checklist",
                            inline=True
                        )
                    ),
                    dbc.Col(
                        width="auto",
                        children=dbc.RadioItems(
                            className="float-right",
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
                children=[
                    dbc.Col(
                        children=dcc.Dropdown(
                            id="maps-dropdown",
                            multi=True,
                            clearable=True,
                            placeholder="Add stops to generate a map...",
                            persistence=True,
                            persistence_type="local"
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
