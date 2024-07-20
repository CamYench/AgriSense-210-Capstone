"""This script will use the tiff files from Landsat data to generate a 'Soil Moisture Index' (SMI) for use in training Agrisense's crop yield prediction model.
SMI is a function of the Land Surface Temperature (LST) of a given area, which is calculated from the Landsat data. The formula for SMI is as follows:
SMI = (LST_max - LST) / (LST_max - LST_min)
"""

from pathlib import Path

import rasterio
import numpy as np

# change this depending on S3 implementation?
DATA_PATH = Path(__file__).parent / "local_data"
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

    
def read_lst_tiff(path:Path, scale_factor:float=0.00341802, offset:float=149.0):
    dataset = rasterio.open(path)
    indexes = dataset.indexes
    if len(indexes) > 1:
        raise ValueError(f"Found {len(indexes)} indexes in file {path.name}.")

    data = dataset.read(1)
    print(f"Read in {path.name}")
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
    return dataset, data

def main():
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