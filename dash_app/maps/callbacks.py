from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_core_components as dcc

from app import app
from common.components import plot_nx
from common.utils import (
    k_shortest_paths,
    shortest_paths,
    style_graph,
    simplify_graph,
    get_subgraph,
    GRAPH
)

import json
import networkx as nx
import time
import igraph as ig

@app.callback(
    Output("maps-plot","children"),
    [Input("maps-dropdown","value"),
    Input("maps-radioitems-input","value")],
    [State("maps-checklist", "value")]
)
def update_plot(station_list, style, modes):

    if station_list is None or len(station_list)<2:
        return None

    G = get_subgraph(modes)

    G_sub = shortest_paths(G, station_list)
    G_sub = simplify_graph(G_sub, simplify_weights=True)
    G_sub = style_graph(G_sub)

    fig = plot_nx(G_sub, station_list, style)
    graph = dcc.Graph(
        figure=fig,
        config={"displayModeBar": False}
    )

    return graph

@app.callback(
    Output("maps-store","data"),
    [Input("url","pathname"),
    Input("maps-checklist","value")]
)
def update_store(_, modes):
    G = get_subgraph(modes)
    options = (
        {"label":f"{v}", "value":k}
        for k,v in zip(G.vs["id"],G.vs["name"])
        if "EntEx" in k
    )
    options = sorted(options, key=lambda t: t["label"])
    return options

@app.callback(
    Output("maps-dropdown", "options"),
    [Input("maps-dropdown", "search_value"),
    Input("maps-dropdown", "value"),
    Input("maps-checklist", "value")],
    [State("maps-store","data")]
)
def update_options(search_value, value, modes, data):

    # make sure that the set values are in the option list, else they will disappear
    # from the shown select list, but still part of the `value`
    clean = lambda s: "".join(s.split()).lower()
    #check = lambda s1,s2: all(x in clean(s2) for x in clean(s1)) if s1 and len(s1)>2 else False
    check = lambda s1,s2: clean(s1) in clean(s2) if s1 and len(s1)>1 else False
    options = [
        o for o in data
        if o["value"] in (value or []) or
        check(search_value, o["label"])
    ]
    return options

@app.callback(
    Output("maps-dropdown","value"),
    [Input("maps-store","data")],
    [State("maps-dropdown","value")]
)
def update_values(data, old_values):
    # old_value is None prevents wrrors in the second list comprehension
    # data is None ensures that the persistent dropdown items work (doesn't seem to always work...)
    if old_values is None or data is None:
        raise PreventUpdate
    data_values = [d["value"] for d in data]
    new_values = [v for v in old_values if v in data_values]
    return new_values

'''
@app.callback(
    Output("maps-dropdown","options"),
    [Input("maps-dropdown","value")],
    [State("maps-dropdown","options")]
)
def update_options(station_list, options_old):

    #with open(f"./common/data_processed/nx_graph_{mode}.json") as f:
    #    #start = time.process_time()
    #    data = json.load(f)
    #    #print(time.process_time() - start)
    #    #start = time.process_time()
    #    G = nx.node_link_graph(data)
    #    #print(time.process_time()-start)
    G = G_map2

    if len(station_list)==0:
        options = [
            {"label":f"{v} [{k}]", "value":k}
            for k,v in zip(G.vs["id"], G.vs["name"])
            if isinstance(v,str) and "EntEx" in k
        ]
        #options = [{"label":v, "value":k} for k,v in nx.get_node_attributes(G,"name").items()
        #    if isinstance(v,str) and "EntEx" in k]
    else:
        station_list_ids = (j for j,v in enumerate(G.vs["id"]) if v in station_list)
        reachable_nodes = set([x for y in station_list_ids for x in G.subcomponent(y,ig.ALL)])
        ###reachable_nodes = set([G.vs["id"][j] for j in reachable_nodes])
        #reachable_nodes = set([x for y in station_list for x in nx.descendants(G,y)])
        all_nodes = set(station_list_ids).union(reachable_nodes)
        #all_nodes = set(station_list).union(reachable_nodes)
        all_names = (v for j,v in enumerate(G.vs["name"]) if j in all_nodes)
        all_ids = (k for j,k in enumerate(G.vs["id"]) if j in all_nodes)
        options = [
            {"label":f"{v} [{k}]", "value":k}
            for v,k in zip(all_names, all_ids)
            if isinstance(v,str) and "EntEx" in k
        ]
        #options = [{"label":v, "value":k} for k,v in nx.get_node_attributes(G,"name").items()
        #    if isinstance(v,str) and "EntEx" in k and k in all_nodes]
    options = sorted(options, key=lambda t: t["label"])

    return options
'''