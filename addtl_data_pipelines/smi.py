"""This script will use the tiff files from Landsat data to generate a 'Soil Moisture Index' (SMI) for use in training Agrisense's crop yield prediction model.
SMI is a function of the Land Surface Temperature (LST) of a given area, which is calculated from the Landsat data. The formula for SMI is as follows:
SMI = (LST_max - LST) / (LST_max - LST_min)
"""

import os
from pathlib import Path

import rasterio
from rasterio import MemoryFile
import numpy as np
import boto3

# change this depending on S3 implementation?
DATA_PATH = Path(__file__).parent / "local_data"
TMP_DIR = Path.home() / "tmp"
TMP_DIR.mkdir(exist_ok=True)
LST_VALID_MIN = 293
LST_VALID_MAX = 61440
SMI_OUT_NO_DATA = -99999.0



def calc_smi_from_lst(lst: np.ndarray):
    if lst.ndim != 2:
        raise ValueError(f"Land Surface Temp data needs to be 2-dimensional")
    lst_max = np.nanmax(lst)
    lst_min = np.nanmin(lst)
    smi = (lst_max - lst) / (lst_max - lst_min)
    print("SMI Calc'd")
    print(f"  min = {np.nanmin(smi)}")
    print(f"  max = {np.nanmax(smi)}")
    return smi

def get_list_of_lst_tiffs(data_path:Path|None=None):
    if not data_path:
        data_path = DATA_PATH
    return [f for f in data_path.glob("*_ST_B10.tif")]

    
def read_lst_tiff(path:Path):
    dataset = rasterio.open(path)
    indexes = dataset.indexes
    if len(indexes) > 1:
        raise ValueError(f"Found {len(indexes)} indexes in file {path.name}.")

    data = dataset.read(1)
    print(f"Read in {path.name}")
    return dataset, data


def process_band_data(data: np.ndarray, scale_factor:float=0.00341802, offset:float=149.0):
    print("Raw")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    data = data.astype(np.float64)

    # replace 0 with nans
    data[data==0.0] = np.nan
    print("0 --> NAN")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    # make within valid range
    data[data < LST_VALID_MIN] = LST_VALID_MIN
    data[data > LST_VALID_MAX] = LST_VALID_MAX
    print("Valid")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    data = data * scale_factor + offset
    print("Scaled - Kelvin")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    # kelvin to celsius
    data = data - 273.15
    print("Scaled - Celsius")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")
    return data

def get_lst_file_paths_from_s3():
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")

    lst_files = []
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if 'ST_B10' in key:
                lst_files.append(key)
    return lst_files




def main():

    use_s3 = True

    if use_s3:

        # retrieve lst files
        lst_files = get_lst_file_paths_from_s3()
    
        for lst_f in lst_files:
            s3_client = boto3.client("s3")
            s3_response = s3_client.get_object(Bucket="agrisense3", Key=lst_f)
            with MemoryFile(s3_response['Body'].read()) as memfile:
                with memfile.open() as src:
                    st_data = process_band_data(src.read(1))
                    smi_data = calc_smi_from_lst(st_data)
                    out_meta = src.meta
            out_meta["dtype"] = "float64"
            out_meta["nodata"] = SMI_OUT_NO_DATA
            out_f_path = lst_f.replace("ST_B10", "SMI")
            out_f_path = out_f_path.replace('converted', str(TMP_DIR))
            with rasterio.open(out_f_path, 'w', **out_meta) as dst:
                dst.write(smi_data, 1)

            print(f'Finished writing tif file to {out_f_path}')
            # upload to s3
            # file locally then upload to s3?
            s3_path = 'smi_output/'+out_f_path.split('/')[-1]
            s3_client.upload_file(out_f_path, 'agrisense3', s3_path)
            print(f"Uploaded to S3 at {s3_path}")

            os.remove(out_f_path)
            print(f'Removed local copy - {not os.path.exists(out_f_path)}')
    else:
    
        lst_tiff_files = get_list_of_lst_tiffs()
        for tiff_file_path in lst_tiff_files:
            out_file_name = str(tiff_file_path).replace("ST_B10", "SMI")
            print("Found")
            print("\t"+str(tiff_file_path))
            print("Creating")
            print("\t"+out_file_name)
    
            # read in tiff_file
            tiff_dataset, tiff_data = read_lst_tiff(tiff_file_path)
    
            smi_data = calc_smi_from_lst(tiff_data)
            # replace nan's with filler
            smi_data[np.isnan(smi_data)] = SMI_OUT_NO_DATA
            print(f"Finished calculating SMI data")
    
            # write tif
            out_tiff_path = Path(out_file_name)
            out_meta = tiff_dataset.meta
            out_meta['dtype'] = "float64"
            out_meta["nodata"] = SMI_OUT_NO_DATA
    
            with rasterio.open(out_tiff_path, 'w', **out_meta) as dst:
                dst.write(smi_data, 1)
    
            print(f"Finished writing SMI to tif file {out_tiff_path.name}")

    print("Done.")


if __name__ == "__main__":
    main()"""This script will use the tiff files from Landsat data to generate a 'Soil Moisture Index' (SMI) for use in training Agrisense's crop yield prediction model.
SMI is a function of the Land Surface Temperature (LST) of a given area, which is calculated from the Landsat data. The formula for SMI is as follows:
SMI = (LST_max - LST) / (LST_max - LST_min)
"""

import os
from pathlib import Path

import rasterio
from rasterio import MemoryFile
import numpy as np
import boto3

# change this depending on S3 implementation?
DATA_PATH = Path(__file__).parent / "local_data"
TMP_DIR = Path.home() / "tmp"
TMP_DIR.mkdir(exist_ok=True)
LST_VALID_MIN = 293
LST_VALID_MAX = 61440
SMI_OUT_NO_DATA = -99999.0



def calc_smi_from_lst(lst: np.ndarray):
    if lst.ndim != 2:
        raise ValueError(f"Land Surface Temp data needs to be 2-dimensional")
    lst_max = np.nanmax(lst)
    lst_min = np.nanmin(lst)
    smi = (lst_max - lst) / (lst_max - lst_min)
    print("SMI Calc'd")
    print(f"  min = {np.nanmin(smi)}")
    print(f"  max = {np.nanmax(smi)}")
    return smi

def get_list_of_lst_tiffs(data_path:Path|None=None):
    if not data_path:
        data_path = DATA_PATH
    return [f for f in data_path.glob("*_ST_B10.tif")]

    
def read_lst_tiff(path:Path):
    dataset = rasterio.open(path)
    indexes = dataset.indexes
    if len(indexes) > 1:
        raise ValueError(f"Found {len(indexes)} indexes in file {path.name}.")

    data = dataset.read(1)
    print(f"Read in {path.name}")
    return dataset, data


def process_band_data(data: np.ndarray, scale_factor:float=0.00341802, offset:float=149.0):
    print("Raw")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    data = data.astype(np.float64)

    # replace 0 with nans
    data[data==0.0] = np.nan
    print("0 --> NAN")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    # make within valid range
    data[data < LST_VALID_MIN] = LST_VALID_MIN
    data[data > LST_VALID_MAX] = LST_VALID_MAX
    print("Valid")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    data = data * scale_factor + offset
    print("Scaled - Kelvin")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")

    # kelvin to celsius
    data = data - 273.15
    print("Scaled - Celsius")
    print(f"  min = {np.nanmin(data)}")
    print(f"  max = {np.nanmax(data)}")
    return data

def get_lst_file_paths_from_s3():
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket="agrisense3", Prefix="converted/")

    lst_files = []
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if 'ST_B10' in key:
                lst_files.append(key)
    return lst_files




def main():

    use_s3 = True

    if use_s3:

        # retrieve lst files
        lst_files = get_lst_file_paths_from_s3()
    
        for lst_f in lst_files:
            s3_client = boto3.client("s3")
            s3_response = s3_client.get_object(Bucket="agrisense3", Key=lst_f)
            with MemoryFile(s3_response['Body'].read()) as memfile:
                with memfile.open() as src:
                    st_data = process_band_data(src.read(1))
                    smi_data = calc_smi_from_lst(st_data)
                    out_meta = src.meta
            out_meta["dtype"] = "float64"
            out_meta["nodata"] = SMI_OUT_NO_DATA
            out_f_path = lst_f.replace("ST_B10", "SMI")
            out_f_path = out_f_path.replace('converted', str(TMP_DIR))
            with rasterio.open(out_f_path, 'w', **out_meta) as dst:
                dst.write(smi_data, 1)

            print(f'Finished writing tif file to {out_f_path}')
            # upload to s3
            # file locally then upload to s3?
            s3_path = 'smi_output/'+out_f_path.split('/')[-1]
            s3_client.upload_file(out_f_path, 'agrisense3', s3_path)
            print(f"Uploaded to S3 at {s3_path}")

            os.remove(out_f_path)
            print(f'Removed local copy - {not os.path.exists(out_f_path)}')
    else:
    
        lst_tiff_files = get_list_of_lst_tiffs()
        for tiff_file_path in lst_tiff_files:
            out_file_name = str(tiff_file_path).replace("ST_B10", "SMI")
            print("Found")
            print("\t"+str(tiff_file_path))
            print("Creating")
            print("\t"+out_file_name)
    
            # read in tiff_file
            tiff_dataset, tiff_data = read_lst_tiff(tiff_file_path)
    
            smi_data = calc_smi_from_lst(tiff_data)
            # replace nan's with filler
            smi_data[np.isnan(smi_data)] = SMI_OUT_NO_DATA
            print(f"Finished calculating SMI data")
    
            # write tif
            out_tiff_path = Path(out_file_name)
            out_meta = tiff_dataset.meta
            out_meta['dtype'] = "float64"
            out_meta["nodata"] = SMI_OUT_NO_DATA
    
            with rasterio.open(out_tiff_path, 'w', **out_meta) as dst:
                dst.write(smi_data, 1)
    
            print(f"Finished writing SMI to tif file {out_tiff_path.name}")

    print("Done.")


if __name__ == "__main__":
    main()