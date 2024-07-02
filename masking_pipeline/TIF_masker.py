#requires existing cropscape strawberry data to exist in ./data/ directory

#import statements
import rasterio
from rasterio.plot import show
from rasterio.enums import Resampling
import pyproj
from matplotlib import pyplot
import numpy as np
import rioxarray
from rioxarray import open_rasterio
import os

def reproject_to_wgs84(file_path,target_path):
    with open_rasterio(file_path) as img:
        reprojected_img = img.rio.reproject('EPSG:4326')
        reprojected_img.rio.to_raster(target_path)


def resample_raster(src_raster, target_raster_profile, resampling_method=Resampling.nearest):
    """
    Resample the source raster to match the target raster's profile.
    """
    with rasterio.open(src_raster) as src:
        data = np.empty((src.count, target_raster_profile['height'], target_raster_profile['width']), dtype=src.dtypes[0])
        transform = target_raster_profile['transform']
        
        for i in range(1, src.count + 1):
            rasterio.warp.reproject(
                source=rasterio.band(src, i),
                destination=data[i - 1],
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_raster_profile['crs'],
                resampling=resampling_method
            )
        return data[0], transform
    

#define function to perform masking
def mask_tif(target_path, source_path, output_path):
    with rasterio.open(target_path) as target:
        target_array = target.read()
        target_profile = target.profile

    #resample source to match the target
    source_resampled, _ = resample_raster(source_path, target_profile)

    #set masking
    threshold = 221
    mask_array = source_resampled == threshold

    # Apply the mask
    masked_array = np.where(mask_array, target_array, 0)

    # Save the masked array to a new TIFF file
    with rasterio.open(output_path, 'w', **target_profile) as dst:
        for i in range(target_array.shape[0]):
            dst.write(masked_array[i].astype('float32'), i+1)

    print(f"Masked TIFF file saved at {output_path}")






for filename in os.listdir('~/data/cropscape'):
    if 'cropscape-strawberries' in filename:
        file_path=os.path.join('~/data', filename)
        if os.path.isfile(file_path):
            target_path=os.path.join('~/data', f'converted-{filename}')
            reproject_to_wgs84(file_path, target_path)
            print(f'Processed {file_path} to {target_path}')


for filename in os.listdir('~/data/landsat_evi_monterey_extracted'):
    if 'SR_EVI' in filename:
        file_path=os.path.join('~/data/landsat_evi_monterey_extracted', filename)
        if os.path.isfile(file_path):
            target_path=os.path.join('~/data/landsat_evi_monterey_extracted/converted', f'converted-{filename}')
            reproject_to_wgs84(file_path, target_path)
            print(f'Processed {file_path} to {target_path}')
    
print('completed')



    





#target directory is the landsat evi files directory, source directory is the masked cropscape directory
target_dir = "~/data/landsat_evi_monterey_extracted/converted"
source_dir = "~/data/cropscape"
dest_dir = "~/data/landsat_evi_monterey_masked"

# Check if destination directory exists, create if it doesn't
if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

# Iterate over each .tif file in the target directory
for target_filename in os.listdir(target_dir):
    if target_filename.endswith('SR_EVI.tif'):
        target_file = os.path.join(target_dir, target_filename)
        year=target_filename[27:31]
        print("Landsat Year:", year)
        source_file = os.path.join(source_dir, f"converted-cropscape-strawberries-06053-{year}.tif")
        output_file = os.path.join(dest_dir, f"{os.path.splitext(target_filename)[0]}_masked.tiff")

        # Check if source file exists
        if os.path.exists(source_file):
            print(f"Processing {target_file} and {source_file}")
            mask_tif(target_file, source_file, output_file)
        else:
            print(f"Source file not found for {target_file}: {source_file}")

print("Processing complete.")