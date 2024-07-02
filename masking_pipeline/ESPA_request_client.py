#This version MUST have the bulk_metadata_file in ./metadata/ directory.
#ONLY works for monterey county

#import statements
import pandas as pd
import requests
import pprint
import urllib.request
from pathlib import Path
import os
import time

#import env variables
espa_password = os.environ["ESPA-PASSWORD"]
target_date = os.environ["TARGET-DATE"] #format target_date='06172024'

#set script variables
path = "./metadata/LANDSAT_OT_C2_L2.csv"
data = pd.read_csv(path)

API_HOST = "https://espa.cr.usgs.gov/api/v1"
USERNAME="pascualeley"
PASSWORD=espa_password


# some conditions defining "California"
# we want to get all images that capture california
ca_min_lat = 32.5
ca_max_lat = 42
ca_min_lon = -124.5
ca_max_lon = -114.0

# define condtitions
# corner upper left
CUL_LAT = (data["Corner Upper Left Latitude"] >= ca_min_lat) & (data["Corner Upper Left Latitude"] <= ca_max_lat)
CUL_LON = (data["Corner Upper Left Longitude"] >= ca_min_lon) & (data["Corner Upper Left Longitude"] <= ca_max_lon)

# corner upper right
CUR_LAT = (data["Corner Upper Right Latitude"] >= ca_min_lat) & (data["Corner Upper Right Latitude"] <= ca_max_lat)
CUR_LON = (data["Corner Upper Right Longitude"] >= ca_min_lon) & (data["Corner Upper Right Longitude"] <= ca_max_lon)

# corner lower left
CLL_LAT = (data["Corner Lower Left Latitude"] >= ca_min_lat) & (data["Corner Lower Left Latitude"] <= ca_max_lat)
CLL_LON = (data["Corner Lower Left Longitude"] >= ca_min_lon) & (data["Corner Lower Left Longitude"] <= ca_max_lon)

# corner lower right
CLR_LAT = (data["Corner Lower Right Latitude"] >= ca_min_lat) & (data["Corner Lower Right Latitude"] <= ca_max_lat)
CLR_LON = (data["Corner Lower Right Longitude"] >= ca_min_lon) & (data["Corner Lower Right Longitude"] <= ca_max_lon)


# ca_data = data[(CUL_LAT & CUL_LON) | (CUR_LAT & CUR_LON ) | (CLL_LAT & CLL_LON) | (CLR_LAT & CLR_LON)]
ca_data = data[(data["Scene Center Latitude"] >= ca_min_lat) & (data["Scene Center Latitude"] <= ca_max_lat) & 
               (data["Scene Center Longitude"] >= ca_min_lon) & (data["Scene Center Longitude"] <= ca_max_lon)]


#filter for montery specific data based on center position

monterey_display_ids=ca_data[
    (ca_data["Scene Center Latitude"] < 37) & (ca_data["Scene Center Latitude"] > 36) &
    (ca_data["Scene Center Longitude"] > -122.1) & (ca_data["Scene Center Longitude"] < -121.0)
    ]["Display ID"].to_list()



def request_data(url:str, json:bool=True, body:dict|None=None, method:str="get"):  
    print("Sending request:")
    print(url)
    if method == "get":
        resp = requests.get(url, auth=(USERNAME, PASSWORD), json=body)
    elif method == "post":
        resp = requests.post(url, auth=(USERNAME, PASSWORD), json=body)
    elif method == "put":
        resp = requests.put(url, auth=(USERNAME, PASSWORD), json=body)
    else:
        return "METHOD NOT SUPPORTED"

    if json:
        return resp.json()
    else:
        return resp



def update_nested_key(data, target_key, new_value):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                data[key] = new_value
            elif isinstance(value, dict):
                update_nested_key(value, target_key, new_value)
            elif isinstance(value, list):
                for item in value:
                    update_nested_key(item, target_key, new_value)
    elif isinstance(data, list):
        for item in data:
            update_nested_key(item, target_key, new_value)


def filter_list_by_string(input_list, filter_string):
    return [item for item in input_list if filter_string in item]



#place orders for existing Monterey Data
for display_id in monterey_display_ids:
    
    endpoint = "/available-products"
    avail_list = {
        "inputs": [display_id] 
    }
    data = request_data(API_HOST + endpoint, body=avail_list)

    endpoint = "/order"
    data['format'] = 'gtiff'
    update_nested_key(data, 'products', ['l1','sr_nvmi','sr_evi','et'])
    resp = request_data(API_HOST + endpoint, body=data, method="post")
          



#get all orders
endpoint = "/list-orders"
all_orders = request_data(API_HOST + endpoint)


# filter for only orders made on target day
all_orders_filtered = filter_list_by_string(all_orders, target_date)

#wait until all filtered orders are complete
for orderid in all_orders_filtered:
    # get status
    endpoint = f"/item-status/{orderid}"
    resp = request_data(API_HOST + endpoint)
    for product in resp[orderid]:
        while product["status"] != "complete":
            time.sleep(10)
                


# get download link for all orders
order_dict = {}

for orderid in all_orders_filtered:

    # get status first
    endpoint = f"/item-status/{orderid}"
    resp = request_data(API_HOST + endpoint)
    # pprint.pprint(resp)
    for product in resp[orderid]:

        if product["status"] == "complete":
            download_url = product["product_dload_url"]
            name = product["name"]
            order_dict[orderid] = {'name':name,'download_url':download_url,'year':ca_data[ca_data['Display ID'] == name]['Date Acquired'].max()}


for order_id, order_details in order_dict.items():
    if 'year' in order_details and isinstance(order_details['year'], str):
        order_details['year'] = order_details['year'].replace('/', '.')


#programmatic download
county = 'Monterey'
for order in order_dict:
    name=order_dict[order]['name']
    download_url=order_dict[order]['download_url']
    date=order_dict[order]['year']
    print(name)
    print(download_url)
    print(date)

    data_dir = Path("~/data/landsat_monterey")
    data_dir.mkdir(exist_ok=True)
    urllib.request.urlretrieve(download_url,data_dir / f"{county}_{date}_{name}.tar.gz" )