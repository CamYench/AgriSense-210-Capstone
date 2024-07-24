
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
    # aws_access_key_id='ASIAZSICGRC5O2STIAHF',
    # aws_secret_access_key='WLKuMMDSAs2wL8LODrqJNcgpMxVEvopK5gc1Y2Tg',
    # aws_session_token='IQoJb3JpZ2luX2VjEL///////////wEaCXVzLWVhc3QtMSJIMEYCIQCAdPeNDcRifPob36+FSNeannCg6LKIj/M6c90otwBZfQIhAIikkSA5vhaKno/+msruWduDkxMZRRKLqyn7XW4Yjbc2KvUCCJj//////////wEQAhoMNjU3NjcxNDg5NzIyIgymCkReJMp6FmJoD9IqyQIx9G+XvUngXlLhCgJPEVgbWKvzg54JOzTnAz70nkAs2J5xG/Hg2fMrMsr7v3LqKnVc8eHliYWaIZKLpcNTfeQSgkE71TRkI0s/2zkilv+EAQiZHv2BQ8WUAbpPy9+FdSC9tFvgU6APMZsoxjSw6xQQP85QWpYx5kqkyuUWhBkKqtmFhh82TWta/oahFd9C7KgcxlDRdkXLkWLgeWyd1mughUv6zlbn4JO4AVNbpLWMSGoR1jbg6IqTejyrZ7lRmuM8KtMlaDuxmjGZUkQ/Lz1D+0E71bAQ+18+MjcYYoh7kIztxH6LulgFW+kDltHmgKj4RcTp3m+UuREUYSHF2d7xy0vCZMQsTu4ikeB0zUeiJ/9SCMNataK6ss4E0IxkRK7XLWvl6hQYSp7qgvBlDnLtCDg2Psz8v0VAlbKFhA2RcKEVsofZ23f9CDDm64C1BjqmAUo4aDrfge4e/9tpvuWHrO1ayfOb25KrlZMCSTjULzicsYxNAUYsRmD4IBFvan8nF37zgL7t7lGhsgKA1WOfATa61E3cRezHjEtipe5r6NMCseS42pV3CxPKp3NiQPF8I46WkgddGPrcADIxwyw3aF9Rkp+lmJbFzIH2RU5M8EoDOyTC7kbOyLjqo49GChZvY1ArIraCdRrqnWkbymkAZW4ynA8/c48=')
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



