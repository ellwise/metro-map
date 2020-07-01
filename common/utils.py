import networkx as nx
import json
from collections import defaultdict
import igraph as ig
import numpy as np

GRAPH = ig.read("./common/data_processed/ig_graph_all.pickle",format="pickle")

def get_subgraph(modes):
    # extract edges with a valid mode plus interchanges
    G = GRAPH.subgraph_edges([
        e for e in GRAPH.es
        if e["mode"] in [*modes,"pedestrian"]
    ], delete_vertices=True)
    # find strongly connected subgraphs
    #Gs = G.decompose(mode=ig.STRONG, maxcompno=1, minelements=2)
    Gs = G.clusters(mode=ig.STRONG)
    # extract the largest subgraph
    j = np.argmax(Gs.sizes())
    G = Gs.subgraph(j)
    #j = np.argmax([g.vcount() for g in Gs])
    #G = Gs[j]
    return G

def k_shortest_paths(G, source_val, target_val, k):

    # find the k-shortest paths
    y = nx.shortest_simple_paths(G, source_val, target_val, weight="weight")
    k_shortest_paths = []
    while len(k_shortest_paths)<k:
        new_path = next(y)
        # doesn't share the same node names
        get_names = lambda path: [G.nodes[u]["name"] for u in path]
        new_names = get_names(new_path)
        old_names = [get_names(path) for path in k_shortest_paths]
        if not new_names in old_names:
            k_shortest_paths.append(new_path)

    # convert to a sub-graph
    ebunch = ((node1, node2, G.edges[node1,node2])
                for path in k_shortest_paths
                    for node1,node2 in zip(path[:-1],path[1:]))
    nbunch = ((node, G.nodes[node]) for path in k_shortest_paths for node in path)

    G_sub = nx.DiGraph()
    G_sub.add_edges_from(ebunch)
    nx.set_node_attributes(G_sub, {k:v for k,v in nbunch})

    return G_sub

def shortest_paths(G, station_list):

    # find the k-shortest paths
    Gp = G.copy()
    Gp.vs["name"] = G.vs["id"]
    Gp.vs["id"] = G.vs["name"]
    shortest_paths = []
    for source_val in station_list:
        target_vals = [v for v in station_list if v!=source_val]
        new_paths = Gp.get_shortest_paths(source_val, to=target_vals, weights="weight", mode=ig.OUT, output="vpath")
        for new_path in new_paths:
            # doesn't share the same node names
            get_names = lambda path: [G.vs["name"][u] for u in path]
            new_names = get_names(new_path)
            old_names = [get_names(path) for path in shortest_paths]
            if not new_names in old_names:
                shortest_paths.append(new_path)

    edges = [edge for path in shortest_paths for edge in zip(path[:-1],path[1:])]
    G_sub = G.subgraph_edges(edges)

    ebunch = (
        (ids[edge[0]], ids[edge[1]], {"line_id":line_id, "weight":weight, "line_name":line_name})
        for ids in [G_sub.vs['id']]
        for edge,line_id,weight,line_name in zip(G_sub.get_edgelist(), G_sub.es["line_id"], G_sub.es["weight"], G_sub.es["line_name"])
    )
    G_nx = nx.DiGraph()
    G_nx.add_edges_from(ebunch)
    nx.set_node_attributes(G_nx, {
        k:{"name":v, "x":x, "y":y}
        for k,v,x,y in zip(G_sub.vs["id"],G_sub.vs["name"],G_sub.vs["x"],G_sub.vs["y"])
    })

    return G_nx

def simplify_graph(G):
    G_sub = nx.DiGraph()
    ebunch = ((node1.split(": ")[1], node2.split(": ")[1], G.edges[node1,node2])
        for node1,node2 in G.edges())
    nbunch = ((node.split(": ")[1], G.nodes[node]) for node in G.nodes())
    G_sub.add_edges_from(ebunch)
    nx.set_node_attributes(G_sub, {k:v for k,v in nbunch})
    #nx.set_edge_attributes(G_sub, 1, name="weight")
    nx.set_edge_attributes(G_sub, {e:(0.001 if G_sub.edges[e]["line_id"]=="pedestrian" else 1) for e in G_sub.edges()}, name="weight")

    return G_sub

def style_graph(G):

    mapping_tube = {
        "bakerloo":"#B36305",
        "central":"#E32017",
        "circle":"#FFD300",
        "district":"#00782A",
        "hammersmith-city":"#F3A9BB",
        "jubilee":"#A0A5A9",
        "metropolitan":"#9B0056",
        "northern":"#000000",
        "piccadilly":"#003688",
        "victoria":"#0098D4",
        "waterloo-city":"#95CDBA"
    }
    mapping_bus = {f"{j}":"#E32017" for j in range(1,1000)}
    mapping_dlr = {"dlr":"#00A4A7"}
    mapping = defaultdict(lambda: "#E32017",
        {
        **mapping_tube,
        **mapping_bus,
        **mapping_dlr,
        "london-overground":"#EF7B10",
        "pedestrian":None
    })

    def colour_node(G,n):
        ebunch = list(G.in_edges(n)) + list(G.out_edges(n))
        line_ids = list({G.edges[u,v]["line_id"] for (u,v) in ebunch})
        if len(line_ids)>1 or line_ids[0]=="pedestrian":
            return {"fill_colour":"#ffffff", "edge_colour":"#000000"}
        else:
            return {"fill_colour":mapping[line_ids[0]], "edge_colour":"#ffffff"}

    nx.set_edge_attributes(G, {(u,v):mapping[line_id] for (u,v,line_id) in G.edges.data("line_id")}, name="fill_colour")
    nx.set_edge_attributes(G, {(u,v):("#000000" if line_id=="pedestrian" else "#ffffff")
                                    for (u,v,line_id) in G.edges.data("line_id")}, name="edge_colour")
    nx.set_node_attributes(G, {u:colour_node(G,u)["fill_colour"] for u in G.nodes()}, name="fill_colour")
    nx.set_node_attributes(G, {u:colour_node(G,u)["edge_colour"] for u in G.nodes()}, name="edge_colour")

    return G