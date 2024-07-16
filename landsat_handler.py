
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
    # aws_access_key_id='ASIAZSICGRC5B2XHPEID',
    # aws_secret_access_key='N+P4boKobJ9eFECriI1zhxtWZ0gbI5lpFf816DCu',
    # aws_session_token='IQoJb3JpZ2luX2VjEAYaCXVzLWVhc3QtMSJIMEYCIQD33WYInlQvRQdPjKjSeTE63OvomDQVzc6Gv5Tkc3T5cAIhAOIYpRIpUu56XYVRFmtMevx6ob5g1S5po8TJ6JA+P7aVKvUCCM///////////wEQAhoMNjU3NjcxNDg5NzIyIgxQg5DUS8JTx4eREcYqyQIqaBEzRDAZ2Ta8hMdC+4rN8uoDVJlUyR+1MOkjIzaAihoLDBTUGLukRpQNnoSVouN8QnjekhC9oxZMGwf2/b5wAun93V4fn9YdPnIHoif2wlsawx7Fn/O32G8CqRHYEy527IWVKDLuy6g9E1m7b/TNGKB7iCqaCBCt9rluXDY8G0KmLq0PJKP9NXFhsWjVPdPpbxHpgYPAJP93m1XEByTpCnYhBs2QqSfTBduouy9iop/Xut7RR1QS/9T316sh+a4ds/nKM8QXx9GUfyWAkV3lzcDBymTY1+4A6IjIAZwXJRLdgM9bmiKXRoEGI13zhXWgmdkxcJmQ0hZmrWJ7hhc6aP6iIh3TEHqtB+soinTBe74Y2QPQLJDX2bqkt/GpCfMfiFyzS4Qt3XwhLMvjKpw5b3C3cSsrZKg2MEYMKauUfdge/jZsqFjj/jCGkti0BjqmAYxr2U1yYHMKM9qS/bF1kx1bl4xatUi7FzJ0GP7CtR2LIMRTicT/GTYzSCmcqyDQHrNZOlssyud456xf0Yf0sVNF0qmKQ5DnETUM58Or/+NvyYqCxtp7sH/oYahLj+Z1JFe+tfZ+MfTO8f2UHtMl3EfPMHQftDJ+Q1VXRZyiehcaxZOOBdfRLD5bgSv/Ov65rtzWIBIsS960QvwOSZDHcIMO9qZ2o2g='
    # )
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")
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
                    date_str = key[17:25]
                    if most_recent_date is None or date_str >= most_recent_date:
                        most_recent_date = date_str
                        latest_evi=key
                except ValueError:
                    continue
            if 'ST_B10' in key:
                try:
                    date_str = key[17:25]
                    if most_recent_date is None or date_str >= most_recent_date:
                        most_recent_date = date_str
                        latest_surface_temp=key
                except ValueError:
                    continue
    
    return (latest_evi, latest_surface_temp, latest_soil_moisture, most_recent_date)
                


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
    s3_response = s3_client.get_object(Bucket='agrisense3', Key='converted/'+image_fn)
    
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



