
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
    # s3_client = boto3.client(
    # 's3',
    # aws_access_key_id='ASIAZSICGRC5IGUMLDVH',
    # aws_secret_access_key='x3I7whN2rs7GVChQj7cyT/PqUUK6vMvIeN/xwvQh',
    # aws_session_token='IQoJb3JpZ2luX2VjEN3//////////wEaCXVzLWVhc3QtMSJIMEYCIQD2asuGwqfEfGYk2WHZCxMclU6X4We3XmwOW3Qx45b1RgIhAPGel695fVjm9z79wZrbcfZpwTjc3UU8PplftPlKTiwsKvUCCLX//////////wEQAhoMNjU3NjcxNDg5NzIyIgwYrRGerdTW8tANC1oqyQKeVEuYo2DBaU6yGPQ1chky7iuGptD8TGmH78eEuoxRT0jE1JDOwRjqqxA4sYqrUJCKfNr1xfEUrjU4I9xVgXBrDflZI2kuBOOfZtX+YLZOWVtT4g2zWFTTHA+LEDBMCy9cfOJPDdjUC9n4lJZ3I007aJWt0awL0KTm1hgMBSEaB6CKq5oCCpUJiLqxw5EcjgDuJbQ/JZH4UR8l3giCnWEl8j7DBNq/5FZ8a81oPpFYYfPCq+N/CwQfo0b97me/pdIsuL+G/lZTyK3tjCxNObqdB/pt+aX2L+YDFz6+8CFz1nTPVEVv9ZNhJjzijLSR6VXKryVebyqeRAd3fWDhELtcaZAtJrG90+Ig6UZKee52Pj5dphvayXTsGsVeoO0g20DGv9jyXN635XJZ8zL+c1AVpZAZIFaaLy+dMks3ZPRrPo/OPdo3wGWbiTD+nYe1BjqmAWrSx++3au7LG8RaeWdnLxmW2qMiviTskvXxgDwhZ+0RzYTlf0bSpFdR6qFBA2wN87vvfnHJctemYI3Nutwr8hfBvY1pTP2N4Hv+YobsZu1VR37nE8uBJ8aZ3lM6q0RFCH8VEHqRuOapRjWofIlF0Bgxd3oRJb7lYmf9pOMR/QG7TX6Gj8LDNJyGeBuX35sycViFRQYm8n5sJd64t3yC6P9DLj+7Pks=')
    
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")
    page_iterator_mtvi = paginator.paginate(Bucket="agrisense3", Prefix="mtvi2_output")
    page_iterator_smi = paginator.paginate(Bucket="agrisense3", Prefix="smi_output")
    # evi_objects = page_iterator.search("Contents[?contains(Key, `EVI`)][]")
    
    
    # create objects
    latest_evi = None
    latest_soil_moisture = None
    latest_surface_temp = None
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
def mask_tif(area_to_mask,image_fn):
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
    

    s3_client = boto3.client('s3')
    #read the file from S3
    # s3_response = s3_client.get_object(Bucket='agrisense3', Key='converted/'+image_fn)
    s3_response = s3_client.get_object(Bucket='agrisense3', Key=image_fn)   
    # Read the file into a memory file
    with MemoryFile(s3_response['Body'].read()) as memfile:
        with memfile.open() as src:
            # Apply the mask
            out_image, out_transform = mask(src, geometries, crop=True)
            out_meta = src.meta

    # Update metadata to reflect the new dimensions
    out_meta.update({
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    return out_image



