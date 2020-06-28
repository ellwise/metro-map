from ingestion import fetch_lines, fetch_routes, fetch_naptan2, fetch_naptan
from processing import process_dfs, build_network

import pandas as pd
import networkx as nx
import json
import numpy as np
from scipy.spatial import cKDTree

# df_lines: mode, name, line_id
# df_routes: name, line_id, naptans, direction
# df_times: line_id, from_naptan, to_naptan, transit_time
# df_loadings:
# df_naptans: naptan, lines, name, lat, lon
# df_flows: 

#df_lines, df_routes, df_times, df_loadings, df_naptans, df_flows = fetch_data2(["bus"], ignore_times=True, update_data=True)

#df = process_dfs(df_routes, df_times, df_naptans, save=False)

#G = build_network(df, save=True)

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

# split the naptans in the routes dataframe
df_routes_split = pd.DataFrame([
    [r,n] for r,_,N,_ in df_routes.itertuples(index=False) for n in N
], columns=["name","naptan"])

# generate inter-station movements via train
df_trains = pd.DataFrame([
    [r,l,nf,nt] for r,l,N,_ in df_routes.itertuples(index=False) for nf,nt in zip(N[:-1],N[1:])
], columns=["name","line_id","naptan_from","naptan_to"])

# generate inter-route transfers
#df_interchanges = pd.merge(
#    left=df_routes_split,
#    right=df_routes_split,
#    on="naptan",
#    suffixes=("_from","_to")
#)
#df_interchanges = df_interchanges[df_interchanges["name_from"]!=df_interchanges["name_to"]]
#df_interchanges["line_id"] = "pedestrian"
df_interchanges = pd.DataFrame()

# generate entrances and exits
df_ex = pd.merge(
    left=df_routes_split,
    right=pd.DataFrame({"name":"EntEx", "naptan":df_routes_split["naptan"].unique()}),
    on="naptan",
    suffixes=("_from","_to")
)
df_ent = pd.merge(
    left=pd.DataFrame({"name":"EntEx", "naptan":df_routes_split["naptan"].unique()}),
    right=df_routes_split,
    on="naptan",
    suffixes=("_from","_to")
)
df_ex["line_id"] = "pedestrian"
df_ent["line_id"] = "pedestrian"

# convert all of the dataframes to a common format
df_trains.rename(inplace=True, columns={"name":"name_from"})
df_trains["name_to"] = df_trains["name_from"]
#df_interchanges.rename(inplace=True, columns={"naptan":"naptan_from"})
#df_interchanges["naptan_to"] = df_interchanges["naptan_from"]
df_ex.rename(inplace=True, columns={"naptan":"naptan_from"})
df_ex["naptan_to"] = df_ex["naptan_from"]
df_ent.rename(inplace=True, columns={"naptan":"naptan_from"})
df_ent["naptan_to"] = df_ent["naptan_from"]

# concatenate them together
df = pd.concat([df_trains,df_interchanges,df_ex,df_ent], ignore_index=True)

# build the network
source_nodes = (df["name_from"] + ": " + df["naptan_from"]).to_list()
target_nodes = (df["name_to"] + ": " + df["naptan_to"]).to_list()
line_ids = df["line_id"].to_list()
ebunch = ((s, t, {"line_id":l}) for s,t,l in zip(source_nodes, target_nodes, line_ids))
G = nx.DiGraph()
G.add_edges_from(ebunch)

# add supplemental edge information
attrs = {(u,v):{"weight":3} for u,v in G.edges()}
nx.set_edge_attributes(G, attrs)

# fetch supplemental node information
#chunksize=10
#all_naptans = list(set(df_routes["naptans"].sum()))
#all_naptans_chunked = [all_naptans[i:i+chunksize] for i in range(0,len(all_naptans),chunksize)]
#dfs_naptans = []
#for naptans in all_naptans_chunked:
#    df_naptans = fetch_naptan2(naptans, update_data=update_data)
#    dfs_naptans.append(df_naptans)
#df_naptans = pd.concat(dfs_naptans, ignore_index=True)
#all_lines = df_lines["line_id"].to_list()
#df_naptans["lines"] = df_naptans["lines"].apply(lambda x: [y for y in x if y in all_lines])
naptans = []
all_naptans = set(df_routes["naptans"].sum())
for naptan in all_naptans:
    new = fetch_naptan(naptan, update_data=update_data)
    naptans.append(new)
naptans = [x for x in naptans if x is not None]
df_naptans = pd.DataFrame.from_records(naptans)
all_lines = df_lines["line_id"].to_list()
df_naptans["lines"] = df_naptans["lines"].apply(lambda x: [y for y in x if y in all_lines])

# attach this supplemental info to the graph nodes
df_supp_routes = pd.merge(
    left=df_routes_split.rename(columns={"name":"route_name"}),
    right=df_naptans[["naptan","name","modes","lat","lon"]],
    on="naptan",
    how="left",
    validate="m:1"
)
df_supp_routes["node"] = df_supp_routes["route_name"] + ": " + df_supp_routes["naptan"]
df_supp_routes.drop(inplace=True, columns=["route_name","naptan"])
df_supp_entex = df_naptans[["naptan","name","modes","lat","lon"]]
df_supp_entex["node"] = "EntEx: " + df_supp_entex["naptan"]
df_supp_entex.drop(inplace=True, columns="naptan")
df_supp = pd.concat([df_supp_routes,df_supp_entex], ignore_index=True)
attrs = {node:{"name":name, "modes":modes, "lat":lat, "lon":lon} for name,modes,lat,lon,node in df_supp.itertuples(index=False)}
nx.set_node_attributes(G, attrs)

# add out-of-station interchanges
if add_out_of_station:
    radius = 6371000
    df = df_naptans[["naptan","name","lat","lon"]]
    df["node"] = df["naptan"].apply(lambda s: f"EntEx: {s}")
    #df = df_supp_routes.copy()
    df["latr"] = df["lat"].apply(np.deg2rad)
    df["lonr"] = df["lon"].apply(np.deg2rad)
    df["cos(latr)"] = df["latr"].apply(np.cos)
    df["sin(latr)"] = df["latr"].apply(np.sin)
    df["cos(lonr)"] = df["lonr"].apply(np.cos)
    df["sin(lonr)"] = df["lonr"].apply(np.sin)
    df["x"] = radius * df["cos(latr)"] * df["cos(lonr)"]
    df["y"] = radius * df["cos(latr)"] * df["sin(lonr)"]
    df["z"] = radius * df["sin(latr)"]
    data = df[["x","y","z"]].values
    tree = cKDTree(data)
    nn_rad = 50
    pairs = tree.query_pairs(nn_rad, p=2)
    # could potentially compute distances from the tree directly...
    df["xyz"] = df[["x","y","z"]].apply(np.array, axis=1)
    j1 = df.columns.get_loc("node")
    j2 = df.columns.get_loc("xyz")
    df_oos = pd.DataFrame(
        [["pedestrian",df.iloc[u,j1],df.iloc[u,j2],df.iloc[v,j1],df.iloc[v,j2]] for u,v in pairs],
        columns=["line_id","node_from","xyz_from","node_to","xyz_to"]
    )
    df_oos["distance"] = (df_oos["xyz_to"]-df_oos["xyz_from"]).apply(np.linalg.norm)
    df_oos.drop(inplace=True, columns=["xyz_from","xyz_to"])
    source_nodes = df_oos["node_from"].to_list()
    target_nodes = df_oos["node_to"].to_list()
    line_ids = df_oos["line_id"].to_list()
    transit_times = df_oos["distance"] / 1.4 / 60 
    ebunch = (
        (s, t, {"line_id":l, "weight":w}) 
        for s,t,l,w in zip(source_nodes, target_nodes, line_ids, transit_times)
        if (s,t) not in G.edges()
    )
    G.add_edges_from(ebunch)
    #note: this includes in-station...

if save:
    data = nx.readwrite.json_graph.node_link_data(G)
    with open("./common/data_processed/nx_graph_all.json", "w") as f:
        json.dump(data, f)
    nx.write_pickle(G, "./common/data_processed/ig_graph_all.pickle")