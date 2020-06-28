import dash_core_components as dcc
import dash_html_components as html

import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import networkx as nx
import numpy as np

def make_blank_figure():
    layout = go.Layout(
        margin=dict(t=0,b=0,l=0,r=0),
        legend=dict(x=0, y=1.05),
        legend_orientation="h",
        legend_itemclick=False, # disable legend interactions (these enable/disable lines)
        legend_itemdoubleclick=False,
        dragmode=False,  # zoomable (problematic generally, and especially on mobile)
        template="plotly_white"
    )
    fig = go.Figure(layout=layout)
    fig.update_xaxes(
        showgrid=False, # thin lines in the background
        zeroline=False, # thick line at x=0
        visible=False,  # numbers below
    )
    fig.update_yaxes(
        showgrid=False, # thin lines in the background
        zeroline=False, # thick line at x=0
        visible=False,  # numbers below
    )
    fig.update_layout()
    return fig

'''
Add a cross-filtered graph of busyness on hover
'''

def plot_nx(G, station_list, style):

    # add interchanges to the station list
    station_list = [s.split(": ")[1] for s in station_list]
    #extra_stations = [c for c,v in nx.get_node_attributes(G,"fill_colour").items() if v=="#ffffff"]
    #station_list += extra_stations

    if style=="schematic":
        pos = nx.spectral_layout(G)
        pos = nx.kamada_kawai_layout(G, pos=pos)
    elif style=="geographical":
        lats = nx.get_node_attributes(G,"lat")
        lons = nx.get_node_attributes(G,"lon")
        circumference_poles = 40008000
        circumference_equator = 40075160
        lat_ref = 51.5074 # london
        ys = {k:lat*circumference_poles/360 for k,lat in lats.items()}
        xs = {k:lon*circumference_equator*np.cos(lat_ref)/360 for k,lon in lons.items()}
        pos = {k:np.array([xs[k],ys[k]]) for k in xs}
    nx.set_node_attributes(G, pos, name="pos")

    edge_traces = []
    colours = [v for _,v in nx.get_edge_attributes(G,"fill_colour").items()]
    names = [v for _,v in nx.get_edge_attributes(G,"line_id").items()]
    unique_colours_names = list(set(zip(colours, names)))
    unique_colours_names = sorted(unique_colours_names, key=lambda x: x[1])
    for colour,name in unique_colours_names:
        edges = [e for e in G.edges() if G.edges[e]["line_id"]==name]
        edge_x = [e for edge in edges for e in [G.nodes[edge[0]]['pos'][0], G.nodes[edge[1]]['pos'][0], None]]
        edge_y = [e for edge in edges for e in [G.nodes[edge[0]]['pos'][1], G.nodes[edge[1]]['pos'][1], None]]
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            mode='lines',
            line=dict(
                color=colour if name!="pedestrian" else "#000000",
                width=3 if name!="pedestrian" else 6
            ),
            name=name.capitalize(),
            showlegend=name!="pedestrian"
        )
        edge_traces.append(edge_trace)
        if name!="pedestrian":
            edge_cx = [(G.nodes[edge[0]]['pos'][0] + G.nodes[edge[1]]['pos'][0])/2 for edge in edges]
            edge_cy = [(G.nodes[edge[0]]['pos'][1] + G.nodes[edge[1]]['pos'][1])/2 for edge in edges]
            edge_trace = go.Scatter(
                x=edge_cx,
                y=edge_cy,
                mode='markers',
                marker=dict(
                    opacity=0,
                    color=colour if name!="pedestrian" else "#ffffff",
                ),
                name="",
                text=[name.capitalize() for _ in edge_cx],
                showlegend=False,
                hoverinfo="text",
            )
            edge_traces.append(edge_trace)
    edges = [e for e in G.edges() if G.edges[e]["line_id"]=="pedestrian"]
    edge_x = [e for edge in edges for e in [G.nodes[edge[0]]['pos'][0], G.nodes[edge[1]]['pos'][0], None]]
    edge_y = [e for edge in edges for e in [G.nodes[edge[0]]['pos'][1], G.nodes[edge[1]]['pos'][1], None]]
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode='lines',
        line=dict(
            color="#ffffff",
            width=2
        ),
        name=name.capitalize(),
        showlegend=False
    )

    node_pos = [v for _,v in nx.get_node_attributes(G,"pos").items()]
    node_x = [v[0] for v in node_pos]
    node_y = [v[1] for v in node_pos]
    node_text_h = [v for _,v in nx.get_node_attributes(G,"name").items()]
    node_text_d = [v if c in station_list else " " for c,v in nx.get_node_attributes(G,"name").items()]
    # note: above there is a bug that means some labels aren't drawn (that should be) if the else case uses an empty string
    simplify_name = lambda s: s.replace(" Underground Station","").replace(" DLR Station","")
    node_text_d = [simplify_name(x) for x in node_text_d]
    node_fill_colour = [v for _,v in nx.get_node_attributes(G,"fill_colour").items()]
    node_edge_colour = [v for _,v in nx.get_node_attributes(G,"edge_colour").items()]
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        text=node_text_d,
        textposition="top center",
        mode='markers+text',
        marker=dict(
            size=10,
            color=node_fill_colour,
            line=dict(
                width=2,
                color=node_edge_colour
            )
        ),
        customdata=node_text_h,
        hovertemplate="%{customdata}",
        showlegend=False,
        name="",
        cliponaxis=False # should let scatter labels flow past edge of chart area but doesn't
    )

    fig = make_blank_figure()
    for trace in [*edge_traces, node_trace, edge_trace]:
        fig.add_trace(trace)

    range_x = max(node_x)-min(node_x)
    range_y = max(node_y)-min(node_y)
    fig.update_xaxes(
        range=[min(node_x)-0.1*range_x, max(node_x)+0.1*range_x]
    )
    fig.update_yaxes(
        scaleanchor="x",
        range=[min(node_y)-0.1*range_y, max(node_y)+0.1*range_y],
        automargin=True
    )


    return fig
