from ingestion import fetch_lines, fetch_routes, fetch_naptan2, fetch_naptan

import pandas as pd
import networkx as nx
import json
import numpy as np
from scipy.spatial import cKDTree
import utm
from sklearn.cluster import DBSCAN
import igraph as ig

modes = ["bus","tube","dlr","overground"]
update_data = False
save = True
add_out_of_station = True

# fetch the line/route data
dfs_lines = []
dfs_routes = []
for mode in modes:
    df_lines = fetch_lines(mode, update_data=update_data)
    dfs_lines.append(df_lines)
    for line_id in df_lines["line_id"].unique():
        for direction in ["inbound","outbound"]:
            df_routes = fetch_routes(line_id, direction, update_data=update_data)
            if not df_routes.empty:
                dfs_routes.append(df_routes)
df_lines = pd.concat(dfs_lines, ignore_index=True)
df_routes = pd.concat(dfs_routes, ignore_index=True)

# fetch all the stops
naptans = []
all_naptans = set(df_routes["naptans"].sum())
for naptan in all_naptans:
    new = fetch_naptan(naptan, update_data=update_data)
    naptans.append(new)
naptans = [x for x in naptans if x is not None]
df_naptans = pd.DataFrame.from_records(naptans)
all_lines = df_lines["line_id"].to_list()
df_naptans["lines"] = df_naptans["lines"].apply(lambda x: [y for y in x if y in all_lines])

# add euclidean coordinates to the stops
xs,ys,_,_ = utm.from_latlon(df_naptans["lat"].values, df_naptans["lon"].values)
df_naptans["x"] = xs
df_naptans["y"] = ys

# split the naptans in the routes dataframe
df_routes_split = pd.DataFrame([
    [r,n] for r,_,N,_ in df_routes.itertuples(index=False) for n in N
], columns=["name","naptan"])

# generate inter-stop movements via metro
df_metro = pd.DataFrame([
    [r,l,nf,nt] for r,l,N,_ in df_routes.itertuples(index=False) for nf,nt in zip(N[:-1],N[1:])
], columns=["name","line_id","naptan_from","naptan_to"])

# generate a dataframe of nodes (routes + naptans)
df_nodes = pd.merge(
    left=df_routes_split,
    right=df_naptans[["naptan","name","x","y"]],
    on="naptan",
    how="left",
    validate="m:1",
    suffixes=("","_stop")
)

# cluster the nodes (give un-clustered points a unique cluster is)
print("Clustering stops...")
clusters = DBSCAN(eps=50, min_samples=2).fit(df_nodes[["x","y"]].values)
df_nodes["cluster_id"] = clusters.labels_
solo_nodes = df_nodes["cluster_id"]==-1
df_nodes.loc[solo_nodes,"cluster_id"] = -df_nodes.index[solo_nodes]

# add a shared entex using aggregation
print("Generating shared nodes...")
df_entex = df_nodes.groupby(by=["cluster_id","name_stop"]) \
    .agg({
        "naptan":list,
        "x":"mean",
        "y":"mean"
    }) \
    .reset_index()
df_entex["naptan"] = df_entex["naptan"].apply(lambda ns: "+".join(set(ns)))
df_entex["name"] = "EntEx"
df_nodes = pd.concat([df_nodes,df_entex], ignore_index=True)

# do a many-to-many join on cluster id for interchanges
print("Computing interchanges...")
df_interchanges = pd.merge(
    left=df_nodes[["name","naptan","cluster_id"]],
    right=df_nodes[["name","naptan","cluster_id"]],
    on="cluster_id",
    suffixes=("_from","_to")
)
df_interchanges.drop(inplace=True, columns="cluster_id")
df_interchanges = df_interchanges[df_interchanges["name_from"]!=df_interchanges["name_to"]]
df_interchanges["line_id"] = "pedestrian"

# convert link dataframes to a common format and combine
df_metro.rename(inplace=True, columns={"name":"name_from"})
df_metro["name_to"] = df_metro["name_from"]
df_edges = pd.concat([df_metro, df_interchanges],ignore_index=True)

# add modes to the link dataframe
print("Adding mode information...")
df_edges = pd.merge(
    left=df_edges,
    right=df_lines.rename(columns={"name":"line_name"}),
    on="line_id",
    how="left",
    validate="m:1"
)
df_edges.loc[df_edges["line_id"]=="pedestrian","mode"] = "pedestrian"
df_edges.loc[df_edges["line_id"]=="pedestrian","line_name"] = "Pedestrian"

# add times to the link dataframe
print("Adding timing information...")
# find distance between stops
df_edges = pd.merge(
    left=df_edges,
    right=df_naptans[["naptan","x","y"]],
    left_on=["naptan_from"],
    right_on=["naptan"],
    how="left",
    validate="m:1"
)
df_edges.rename(inplace=True, columns={"x":"x_from","y":"y_from"})
df_edges.drop(inplace=True, columns="naptan")
df_edges = pd.merge(
    left=df_edges,
    right=df_naptans[["naptan","x","y"]],
    left_on=["naptan_to"],
    right_on=["naptan"],
    how="left",
    validate="m:1"
)
df_edges.rename(inplace=True, columns={"x":"x_to","y":"y_to"})
df_edges.drop(inplace=True, columns="naptan")
df_edges["dx"] = df_edges["x_to"] - df_edges["x_from"]
df_edges["dy"] = df_edges["y_to"] - df_edges["y_from"]
df_edges.drop(inplace=True, columns=["x_from","y_from","x_to","y_to"])
df_edges["dx2"] = df_edges["dx"] * df_edges["dx"]
df_edges["dy2"] = df_edges["dy"] * df_edges["dy"]
df_edges.drop(inplace=True, columns=["dx","dy"])
df_edges["dist2"] = df_edges["dx2"] + df_edges["dy2"]
df_edges.drop(inplace=True, columns=["dx2","dy2"])
df_edges["distance"] = df_edges["dist2"].apply(np.sqrt)
df_edges.drop(inplace=True, columns=["dist2"])
# use speed to determine time between stops
df_speeds = pd.read_csv("./common/data_processed/speed_by_line.csv")
df_edges = pd.merge(
    left=df_edges,
    right=df_speeds,
    on=["line_id","mode"],
    how="left",
    validate="m:1"
)
df_edges["weight"] = df_edges["distance"] / df_edges["speed"]
# add a default for pedestrian links
df_edges.loc[df_edges["line_id"]=="pedestrian","weight"] = 3
# deal with missing bus values
mask = df_edges["weight"].isna() & df_edges["mode"].isin(["bus"])
med_bus_speed = df_speeds.loc[df_speeds["mode"]=="bus","speed"].median()
df_edges.loc[mask,"weight"] = df_edges.loc[mask,"distance"] / med_bus_speed
#print(df_edges[df_edges["weight"].isna()].head()) # check we've assigned all the weights...
df_edges.drop(inplace=True, columns=["distance","speed"])

# build the network
print("Building network...")
source_nodes = (df_edges["name_from"] + ": " + df_edges["naptan_from"]).to_list()
target_nodes = (df_edges["name_to"] + ": " + df_edges["naptan_to"]).to_list()
line_ids = df_edges["line_id"].to_list()
modes = df_edges["mode"].to_list()
line_names = df_edges["line_name"].to_list()
weights = df_edges["weight"].to_list()
ebunch = (
    (s, t, {"line_id":l, "mode":m, "line_name":n, "weight":w})
    for s,t,l,m,n,w in zip(source_nodes, target_nodes, line_ids, modes, line_names, weights)
)
G = nx.DiGraph()
G.add_edges_from(ebunch)

# add supplemental node information
df_nodes["node"] = df_nodes["name"] + ": " + df_nodes["naptan"]
attrs = {node:{"name":name, "naptan":naptan, "x":x, "y":y} for _,naptan,name,x,y,_,node in df_nodes.itertuples(index=False)}
nx.set_node_attributes(G, attrs)

if save:
    print("Saving graph...")
    #data = nx.readwrite.json_graph.node_link_data(G)
    #with open("./common/data_processed/nx_graph_all.json", "w") as f:
    #    json.dump(data, f)
    nx.write_graphml(G, "./common/data_processed/nx_graph_all.graphml")
    G = ig.load("./common/data_processed/nx_graph_all.graphml")
    G.save("./common/data_processed/ig_graph_all.pickle")