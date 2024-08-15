
import boto3
import rasterio
import geojson

from rasterio.io import MemoryFile
from rasterio.mask import mask
from shapely.geometry import shape
import json


#tasks
#find most recent landsat images from S3 file (secondary: must cover entire land area)
#currently assumes that multiple images from the same date do not exist


def retrieve_latest_images():
    # Initialize S3 client and search client
    s3_client = boto3.client('s3')

    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")
    page_iterator_mtvi = paginator.paginate(Bucket="agrisense3", Prefix="mtvi2_output")
    page_iterator_smi = paginator.paginate(Bucket="agrisense3", Prefix="smi_output")
    # evi_objects = page_iterator.search("Contents[?contains(Key, `EVI`)][]")
    
    
    # create objects
    latest_evi = None
    latest_smi = None
    latest_mtvi = None
    most_recent_date = None

    #iterate through bucket
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key=obj['Key']
            if 'EVI' in key:
                try:
                    date_str = key[27:35]
                    if most_recent_date is None or date_str >= most_recent_date:
                        most_recent_date = date_str
                        latest_evi=key
                except ValueError:
                    continue
            if 'ST_B10' in key:
                try:
                    date_str = key[27:35]
                    if most_recent_date is None or date_str >= most_recent_date:
                        most_recent_date = date_str
                        latest_surface_temp=key
                except ValueError:
                    continue

    for page in page_iterator_mtvi:
        for obj in page.get('Contents', []):
            key=obj['Key']
            if 'MTVI2' in key:
                try:
                    date_str = key[30:38]
                    if date_str == most_recent_date:
                        latest_mtvi=key
                except ValueError:
                    continue

    for page in page_iterator_smi:
        for obj in page.get('Contents', []):
            key=obj['Key']
            if 'SMI' in key:
                try:
                    date_str = key[28:36]
                    if date_str == most_recent_date:
                        latest_smi=key
                except ValueError:
                    continue
    

    return (latest_evi, latest_surface_temp, latest_smi, latest_mtvi, most_recent_date)


def retrieve_last_4_evi():
    # Initialize S3 client and search client
    s3_client = boto3.client('s3')

    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")
    
    #list of EVI files present
    evi_files = []

    #iterate through bucket
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key=obj['Key']
            if 'EVI' in key:
                try:
                    date_str = key[27:35]
                    evi_files.append((date_str, key))
                except ValueError:
                    continue
    
    evi_files.sort(reverse=True, key=lambda x: x[0])
    latest_4_evi = [key for date, key in evi_files[:4]]

    return (latest_4_evi)


def retrieve_last_4_masked():
    # Initialize S3 client and search client
    s3_client = boto3.client('s3')

    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="landsat_masked/")
    
    #list of EVI files present
    evi_files = []

    #iterate through bucket
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key=obj['Key']
            if 'EVI' in key:
                try:
                    date_str = key[32:40]
                    evi_files.append((date_str, key))
                except ValueError:
                    continue
    
    evi_files.sort(reverse=True, key=lambda x: x[0])
    latest_4_masked = [key for date, key in evi_files[:4]]

    return (latest_4_masked)
                


#convert input area to WGS-84
def convert_selected_area(coordinates):
    """
    inputs
    coordinates: raw GeoJSON from user_input

    outputs
    converted_coordinates: GeoJSON format coordinates transformed to WGS84
    """
    pass


#mask based on current selection geojson
def mask_tif(area_to_mask,image_fn, crop=True):
    """
    inputs
    area_to_mask: GeoJSON coordinates shape (could be rectangle or freeform)
    image_fn: tif of satelite data
    All items must be converted to WGS84 prior to function

    outputs
    out_image: masked image object

    """
    
    if "geometry" in area_to_mask:
        geometries = [area_to_mask["geometry"]]
    elif "features" in area_to_mask:
        geometries = [feature["geometry"] for feature in area_to_mask["features"]]
    
    #read the local image
    img = rasterio.open(image_fn)
    with img as src: 
        # Apply the mask
        out_image, out_transform = mask(src, geometries, crop=crop)
        out_meta = src.meta

    # Update metadata to reflect the new dimensions
    out_meta.update({
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    return out_image



