
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
    # s3_client = boto3.client('s3')
    s3_client = boto3.client(
    's3',
    aws_access_key_id='ASIAZSICGRC5F3K5DWHH',
    aws_secret_access_key='SSsMBrjuUe9FiwLrZKYrucHLJPgKHkf13icOP8xK',
    aws_session_token='IQoJb3JpZ2luX2VjEI7//////////wEaCXVzLWVhc3QtMSJGMEQCIAkROXN5Vgs9RB3ukR7ASSn89a8mYeBw5NdWwLVTEDSUAiAs4gunXReQ/+nJtAg/9foxDg9K85H6cqaupRGC42+v7yrsAghmEAIaDDY1NzY3MTQ4OTcyMiIMW7boLu1gCv36cb/RKskCs/GKmkoYWiDgJf4GYungxYnYY39QGZoDS93Fn3AjMNGBh4R/ItBFIRNt0psUFDo6riGFngqE1pxaECqP4Lf1gBhQmI8x1KTQ4FQ6WhPorGu0DfIwOpgRdISxcwK3m55zafiQn9msMWWJEoyFU58x/UZ+XjU/upltLjN5vF9g7F+8uZVHWpJTg/kTEBbIJhPLJi/Z5un+TbKBhwVMrcBA19QOSR2nWqXetjBYtiRorufcz12ivejLpOIHhCstizMw3TnxM1jCeUFxrTtEPskIt35HUmNQjsZY2dDSDuZWUIB+l4clF2N1cAQ40agAmQEnCTmUwsytToxPUtOAtNU/AyjTgLebdU38SpP/OU9iQrjbnh7cjMXi/hO6J+JVTddCl0kkB98QRqOYYg+wWLawdYmTiffeWNwipBDdt69gcJDlV9fDwk0AeRUwsvH1tAY6qAEmzr/RYnmF7eNLwFyzP9qJKuBLDl4qIfOmml+5ySJbTBa0QSBvnRsDfU2ifGHJFfm5uvRTe1zUH0USNNEGpoT3rZgcLq1Dif451MBsmPEtpm+Ltw8N7dCJZ8cbTUB47dp7bdLq+tcVP2bl29ppSc2X3z4qEcui/5duanPz8KY6qHCJlfmcmZ7cev+vYcp0CL3e85NSPQguwG7p+jK+sKnFhgEd4BGSRE0='
)
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



