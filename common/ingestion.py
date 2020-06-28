import pandas as pd
import os
import json
import requests
import datetime
import time

def make_query(
    query,
    path="./common/data_raw/tfl_api2/",
    verbose=True,
    update=False,
    app_id="65d0aab0",
    app_key="cdd81044920314738d75500411d1b504"
    ):
    if verbose:
        print(query)
    if update:
        url = f"https://api.tfl.gov.uk{query}app_id={app_id}&app_key={app_key}"
        response = requests.get(url)
        parsed = json.loads(response.text)
        latest_date = datetime.date.today().strftime('%Y-%m-%d')
        os.makedirs(path+latest_date+os.path.split(query)[0], exist_ok=True)
        with open(f"{path}{latest_date}{query[:-1]}.json", "w") as f:
            json.dump(parsed, f)
    else:
        latest_date = sorted(os.listdir(path))[-1]
        with open(f"{path}{latest_date}{query[:-1]}.json", "r") as f:
            parsed = json.load(f)
    return parsed

def fetch_data(mode, update_data=False):

    df_routes = pd.DataFrame({"name":[], "line_id":[]})
    df_times = pd.DataFrame({"route":[], "line_id":[], "from_naptan":[], "to_naptan":[], "transit_time":[]})
    df_stations = pd.DataFrame({"name":[], "line_id":[], "naptan":[], "lat":[], "lon":[]})

    # find the the lines for the given mode
    query = f"/Line/Mode/{mode}?"
    json_lines = make_query(query, update=update_data)
    
    # find the stations and routes for each line
    for json_line in json_lines:
        line_id = json_line["id"]
        
        # find the stations
        query = f"/Line/{line_id}/StopPoints?"
        json_stations = make_query(query, update=update_data)
        for entity in json_stations:
            naptan = entity["naptanId"]
            crowdingType = "passengerFlows"
            crowding_inbound = fetch_crowding(naptan, line_id, "inbound", crowdingType, update_data=True)
            crowding_outbound = fetch_crowding(naptan, line_id, "outbound", crowdingType, update_data=True)
            station = {
                "name":entity["commonName"],
                "line_id":line_id,
                "naptan":naptan,
                "lat":entity["lat"],
                "lon":entity["lon"],
                "crowding":{
                    "inbound":crowding_inbound,
                    "outbound":crowding_outbound
                }
            }
            print(station)
            dafsfsadfsad
            df_stations = df_stations.append(station, ignore_index=True)
        
        # find the routes
        for direction in ["inbound","outbound"]:
            query = f"/Line/{line_id}/Route/Sequence/{direction}?"
            json_routes = make_query(query, update=update_data)
            
            # record data from each route
            for json_route in json_routes["orderedLineRoutes"]:
                name = json_route["name"]
                naptan_ids = json_route["naptanIds"]
                route = {
                    "name":name,
                    "line_id":line_id
                }
                df_routes = df_routes.append(route, ignore_index=True)
                    
                # record journey times
                query = f"/Line/{line_id}/Timetable/{naptan_ids[0]}/To/{naptan_ids[-1]}?"
                json_times = make_query(query, update=update_data)

                try:
                    for route in json_times["timetable"]["routes"]:              
                        for station_intervals in route["stationIntervals"]:
                            # do the intervals match the route waypoints?
                            test_naptan_ids = [naptan_ids[0]]
                            for interval in station_intervals["intervals"]:
                                test_naptan_ids.append(interval["stopId"])
                            # if yes, then record the timings
                            if naptan_ids==test_naptan_ids:
                                succeeded_for_route = True
                                last_time_to_arrival = 0
                                from_naptan = naptan_ids[0]
                                for interval in station_intervals["intervals"]:
                                    to_naptan = interval["stopId"]
                                    current_time_to_arrival = interval["timeToArrival"]
                                    transit_time = current_time_to_arrival-last_time_to_arrival
                                    times = {
                                        "route":name,
                                        "line_id":line_id,
                                        "from_naptan":from_naptan,
                                        "to_naptan":to_naptan,
                                        "transit_time":transit_time
                                    }
                                    df_times = df_times.append(times, ignore_index=True)
                                    last_time_to_arrival = current_time_to_arrival
                                    from_naptan = to_naptan
                except:
                    print("timetable error")

    return df_routes, df_stations, df_times

def fetch_lines(mode, update_data=False):

    df_lines = pd.DataFrame({"mode":[], "name":[], "line_id":[]})

    # find the the lines for the given mode
    query = f"/Line/Mode/{mode}?"
    json_lines = make_query(query, update=update_data)

    # find the stations and routes for each line
    for json_line in json_lines:
        line = {
            "mode":mode,
            "name":json_line["name"],
            "line_id":json_line["id"]
        }
        df_lines = df_lines.append(line, ignore_index=True)

    return df_lines
    
def fetch_routes(line_id, direction, update_data=False):

    try:
        df_routes = pd.DataFrame({"name":[], "line_id":[], "naptans":[]})
            
        # find the routes
        query = f"/Line/{line_id}/Route/Sequence/{direction}?"
        json_routes = make_query(query, update=update_data)
            
        # record data from each route
        for json_route in json_routes["orderedLineRoutes"]:
            name = json_route["name"]
            naptan_ids = json_route["naptanIds"]
            route = {
                "name":name,
                "line_id":line_id,
                "naptans":naptan_ids,
                "direction":direction
            }
            df_routes = df_routes.append(route, ignore_index=True)
                        
        return df_routes
    except:
        print("Failed to fetch routes.")
        return pd.DataFrame()

def fetch_loadings(from_naptan, to_naptan, line_id, update_data=False):
    crowdingType = "trainLoadings"
    dfs = []
    direction = make_query(f"/StopPoint/{from_naptan}/DirectionTo/{to_naptan}?", update=update_data)
    parsed = make_query(f"/StopPoint/{from_naptan}/Crowding/{line_id}?direction={direction}&", update=update_data)
    try:
        for entity in parsed["lines"]:
            if entity["id"]==line_id:
                df = pd.DataFrame.from_records(entity["crowding"][crowdingType])
                df.drop(inplace=True, columns=["$type","naptanTo","line","lineDirection","platformDirection","direction"])
                dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)
        # convert timeSlice to start-time
        df["time_start"] = df["timeSlice"].apply(lambda s: datetime.datetime.strptime(s.split("-")[0], "%H%M"))
        df.drop(inplace=True, columns="timeSlice")
        df.groupby(by="time_start").agg({"value":"mean"}).reset_index()
        df.sort_values(inplace=True, by="time_start")
        return {
            "from_naptan":from_naptan,
            "to_naptan":to_naptan,
            "line_id":line_id,
            "loading":df.to_dict("records")
        }
    except:
        print("Failed to fetch loading.")
        return {}

# need to work out what inbound and outbound mean here...
def fetch_flows(naptan, line_id, direction, update_data=False):
    crowdingType = "passengerFlows"
    dfs = []
    parsed = make_query(f"/StopPoint/{naptan}/Crowding/{line_id}?direction={direction}&", update=update_data)
    try:
        for entity in parsed["lines"]:
            if entity["id"]==line_id:
                df = pd.DataFrame.from_records(entity["crowding"][crowdingType])
                df.drop(inplace=True, columns="$type")
                dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)
        # convert timeSlice to start-time
        df["time_start"] = df["timeSlice"].apply(lambda s: datetime.datetime.strptime(s.split("-")[0], "%H%M"))
        df.drop(inplace=True, columns="timeSlice")
        df.groupby(by="time_start").agg({"value":"mean"}).reset_index()
        df.sort_values(inplace=True, by="time_start")
        return {
            "naptan":naptan,
            "line_id":line_id,
            "direction":direction,
            "flow":df.to_dict("records")
        }
    except:
        print("Failed to fetch flow.")
        return {}

def fetch_times(line_id, naptan_ids, update_data=False):
    df_times = pd.DataFrame({"line_id":[], "from_naptan":[], "to_naptan":[], "transit_time":[]})
    # record journey times
    try:
        query = f"/Line/{line_id}/Timetable/{naptan_ids[0]}/To/{naptan_ids[-1]}?"
        json_times = make_query(query, update=update_data)
        for route in json_times["timetable"]["routes"]:              
            for station_intervals in route["stationIntervals"]:
                # do the intervals match the route waypoints?
                test_naptan_ids = [naptan_ids[0]]
                for interval in station_intervals["intervals"]:
                    test_naptan_ids.append(interval["stopId"])
                # if yes, then record the timings
                if naptan_ids==test_naptan_ids:
                    succeeded_for_route = True
                    last_time_to_arrival = 0
                    from_naptan = naptan_ids[0]
                    for interval in station_intervals["intervals"]:
                        to_naptan = interval["stopId"]
                        current_time_to_arrival = interval["timeToArrival"]
                        transit_time = current_time_to_arrival-last_time_to_arrival
                        times = {
                            "line_id":line_id,
                            "from_naptan":from_naptan,
                            "to_naptan":to_naptan,
                            "transit_time":transit_time
                        }
                        df_times = df_times.append(times, ignore_index=True)
                        last_time_to_arrival = current_time_to_arrival
                        from_naptan = to_naptan
    except:
        print(f"{json_times['httpStatusCode']}: {json_times['message']}")

    return df_times

def fetch_naptan(naptan, update_data=False):
    query = f"/StopPoint/{naptan}?"
    parsed = make_query(query, update=update_data)
    lines = [x["id"] for x in parsed["lines"]]
    return {
        "naptan":naptan,
        "modes":", ".join(parsed["modes"]),
        "lines":lines,
        "name":parsed["commonName"],
        "lat":parsed["lat"],
        "lon":parsed["lon"]
    }

def fetch_naptan2(naptans, update_data=False):
    naptans_str = ",".join(naptans)
    query = f"/StopPoint/{naptans_str}?"
    parsed = make_query(query, update=update_data)
    records = []
    for naptan,elem in zip(naptans,parsed): # this assumes they're in order!
        lines = [x["id"] for x in elem["lines"]]
        records.append({
            "naptan":naptan,
            "lines":lines,
            "name":elem["commonName"],
            "lat":elem["lat"],
            "lon":elem["lon"]
        })
    df_naptans = pd.DataFrame.from_dict(records)
    return df_naptans

def fetch_crowding(naptans, update_data=False):
    naptans_str = ",".join(naptans)
    query = f"/StopPoint/{naptans_str}?includeCrowdingData=true&"
    parsed = make_query(query, update=update_data)
    records = []
    for elem in parsed:
        naptan = elem["naptanId"]
        lines = [x["id"] for x in elem["lines"]]
        records.append({
            "naptan":naptan,
            "lines":lines,
            "name":elem["commonName"],
            "lat":elem["lat"],
            "lon":elem["lon"]
        })
    df_naptans = pd.DataFrame.from_dict(records)
    flow_records = []
    loading_records = []
    for elem in parsed:
        naptan = elem["naptanId"]
        for line in elem["lines"]:
            line_id = line["id"]
            try:
                crowding = line["crowding"]
                flow_records += [{
                    "naptan":naptan,
                    "line_id":line_id,
                    "timeSlice":x["timeSlice"],
                    "value":x["value"]
                } for x in crowding["passengerFlows"]]
            except:
                print("Failed to fetch flow data.")
            try:
                crowding = line["crowding"]
                loading_records += [{
                    "timeSlice":x["timeSlice"],
                    "value":x["value"],
                    "line_id":line_id,
                    "direction":x["direction"],
                    "from_naptan":naptan,
                    "to_naptan":x["naptanTo"]
                } for x in crowding["trainLoadings"]]
            except:
                print("Failed to fetch loading data.")
    df_flows = pd.DataFrame.from_records(flow_records)
    df_loadings = pd.DataFrame.from_records(loading_records)

    return df_naptans, df_flows, df_loadings

def fetch_data2(modes, ignore_times=False, update_data=False):

    dfs_lines = []
    dfs_routes = []
    dfs_times = []
    for mode in modes:
        df_lines = fetch_lines(mode, update_data=update_data)
        dfs_lines.append(df_lines)
        for line_id in df_lines["line_id"].unique():
            for direction in ["inbound","outbound"]:
                df_routes = fetch_routes(line_id, direction, update_data=update_data)
                if not df_routes.empty:
                    dfs_routes.append(df_routes)
                    if ignore_times:
                        for naptan_ids in df_routes["naptans"]:
                            df_times = pd.DataFrame({
                                "from_naptan":naptan_ids[:-1],
                                "to_naptan":naptan_ids[1:],
                            })
                            df_times["line_id"] = line_id
                            df_times["transit_time"] = 1
                            dfs_times.append(df_times)
                    else:
                        for naptan_ids in df_routes["naptans"]:
                            df_times = fetch_times(line_id, naptan_ids, update_data=update_data)
                            dfs_times.append(df_times)
    df_lines = pd.concat(dfs_lines, ignore_index=True)
    df_routes = pd.concat(dfs_routes, ignore_index=True)
    df_times = pd.concat(dfs_times, ignore_index=True)

    loadings = []
    #for j,row in df_times[["line_id","from_naptan","to_naptan"]].drop_duplicates().iterrows():
    #    loadings.append(fetch_loadings(
    #        row["from_naptan"],
    #        row["to_naptan"],
    #        row["line_id"],
    #        update_data=update_data
    #    ))
    df_loadings = pd.DataFrame.from_records(loadings)

    #naptans = []
    #all_naptans = set(df_routes["naptans"].sum())
    #for naptan in all_naptans:
    #    naptans.append(fetch_naptan(naptan, update_data=update_data))
    #df_naptans = pd.DataFrame.from_records(naptans)
    ## filter naptan lines to those we're using above
    #all_lines = df_lines["line_id"].to_list()
    #df_naptans["lines"] = df_naptans["lines"].apply(lambda x: [y for y in x if y in all_lines])

    chunksize=10
    all_naptans = list(set(df_routes["naptans"].sum()))
    all_naptans_chunked = [all_naptans[i:i+chunksize] for i in range(0,len(all_naptans),chunksize)]
    dfs_naptans = []
    for naptans in all_naptans_chunked:
        df_naptans = fetch_naptan2(naptans, update_data=update_data)
        dfs_naptans.append(df_naptans)
    df_naptans = pd.concat(dfs_naptans, ignore_index=True)
    #df_naptans.drop_duplicates(inplace=True, subset="naptan")
    all_lines = df_lines["line_id"].to_list()
    df_naptans["lines"] = df_naptans["lines"].apply(lambda x: [y for y in x if y in all_lines])

    flows = []
    #for j,row in df_naptans.iterrows():
    #    naptan = row["naptan"]
    #    for line_id in row["lines"]:
    #        for direction in ["inbound","outbound"]:
    #            flows.append(fetch_flows(naptan, line_id, direction, update_data=update_data))
    df_flows = pd.DataFrame.from_records(flows)

    return df_lines, df_routes, df_times, df_loadings, df_naptans, df_flows

