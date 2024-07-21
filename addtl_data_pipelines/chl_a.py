"""Simlar to smi.py, except this one is more complicated. We'll be using data from a few bands to create an approximation for chlorophyll content of vegetation.
This script will calculate the 'Modified Triangular Vegetation Index 2 (MTVI2).
Research has show this index to be the best metric for measuring chlorophyll content using remote sensing.
"""

from pathlib import Path

import numpy as np
import rasterio
import rasterio.io

DATA_PATH = Path(__file__).parent / "local_data"


# band specs for surface reflectance
# specs are different for surface temperature
BAND_RANGE = (1, 65535)
VALID_RANGE = (7273, 43636)
FILL_VALUE = 0
SCALE_FACTOR = 0.0000275
ADDITIVE_OFFSET = -0.2
RED_BAND = "B4"
GREEN_BAND = "B3"
NIR_BAND = "B5"


class BandSpecs:
    def __init__(
        self,
        band_range: tuple[int, int] = BAND_RANGE,
        valid_range: tuple[int, int] = VALID_RANGE,
        fill_value: int = FILL_VALUE,
        scale_factor: float = SCALE_FACTOR,
        additive_offset: float = ADDITIVE_OFFSET,
        red: str = RED_BAND,
        green: str = GREEN_BAND,
        nir: str = NIR_BAND,
    ):
        self.band_range = band_range
        self.band_range_min = self.band_range[0]
        self.band_range_max = self.band_range[1]

        self.valid_range = valid_range
        self.valid_range_min = self.valid_range[0]
        self.valid_range_max = self.valid_range[1]
        self.scale_factor = scale_factor
        self.additive_offset = additive_offset

        self.fill_value = fill_value

        self.red_bidx = red
        self.green_bidx = green
        self.nir_bidx = nir


def calc_mtvi2(R_nir: np.ndarray, R_green: np.ndarray, R_red: np.ndarray):
    if R_nir.ndim != R_green.ndim != R_red.ndim != 2:
        raise ValueError(
            f"# of dimensions do not match for Band data.\
                         \n  {R_nir.ndim = }\n  {R_green.ndim = }\n  {R_red.ndim = }"
        )

    numerator = 1.5 * (1.2 * (R_nir - R_green) - 2.5 * (R_red - R_green))
    denominator = np.sqrt((2 * R_nir + 1) ** 2 - (6 * R_nir - 5 * np.sqrt(R_red)) - 0.5)

    return numerator / denominator


def process_band(band: np.ndarray, band_specs: BandSpecs, logging: bool = True):
    """
    Process a band of data by performing the following steps:
    1. Check if the band is a 2-dimensional array.
    2. Create a copy of the band data.
    3. Replace any fill values specified by 'band_specs' to NANs.
    4. Ensure that the data is within the valid range specified by `band_specs`.
    5. Convert the data to reflectance using the scale factor and additive offset specified by `band_specs`.

    Parameters:
        band (np.ndarray): The input band data as a 2-dimensional array.
        band_specs (BandSpecs): The specifications for the band, including the valid range, scale factor, and additive offset.
        logging (bool, optional): Whether to log the intermediate steps. Defaults to True.

    Returns:
        np.ndarray: The processed band data.

    Raises:
        ValueError: If the input band is not a 2-dimensional array.
    """
    if band.ndim != 2:
        raise ValueError("Band should be a 2-dimensional array.")

    data = band.copy()

    # print stats
    if logging:
        print("Raw")
        print(f"  min = {np.nanmin(data)}")
        print(f"  max = {np.nanmax(data)}")

    # convert from int to float to replace 0 w/ NANs
    data = data.astype(np.float64)
    data[data == band_specs.fill_value] = np.nan

    # print stats
    if logging:
        print("0 --> NAN")
        print(f"  min = {np.nanmin(data)}")
        print(f"  max = {np.nanmax(data)}")

    # make within valid range
    data[data < band_specs.valid_range_min] = band_specs.valid_range_min
    data[data > band_specs.valid_range_max] = band_specs.valid_range_max

    # print stats
    if logging:
        print("Valid")
        print(f"  min = {np.nanmin(data)}")
        print(f"  max = {np.nanmax(data)}")

    # convert to reflectance
    data = data * band_specs.scale_factor + band_specs.additive_offset

    # print stats
    if logging:
        print("Reflectance")
        print(f"  min = {np.nanmin(data)}")
        print(f"  max = {np.nanmax(data)}")

    return data


def process_file(path: Path, band_specs: BandSpecs):
    """
    Process a raster file and return the dataset reader and the processed data.

    Args:
        path (Path): The path to the raster file.
        band_specs (BandSpecs): The specifications for processing the band data.

    Returns:
        Tuple[rasterio.io.DatasetReader, np.ndarray]: A tuple containing the dataset reader
        and the processed data.

    Raises:
        ValueError: If more than one band is found in the raster file.
    """
    rio_dataset_reader = rasterio.open(path)  # type: rasterio.io.DatasetReader
    indexes = rio_dataset_reader.indexes
    if len(indexes) > 1:
        raise ValueError(f"Found {len(indexes)} indexes in file {path.name}.")

    band_data = rio_dataset_reader.read(1)  # type: np.ndarray
    processed_data = process_band(band_data, band_specs)
    return rio_dataset_reader, processed_data


def process_grouped_files(grouped_files: dict[str, Path], band_specs: BandSpecs):
    grouped_data: dict[str, tuple[rasterio.io.DatasetReader, np.ndarray]] = {}
    for band_name, band_file_path in grouped_files.items():
        rio_dataset_reader, data = process_file(band_file_path, band_specs)
        grouped_data[band_name] = (rio_dataset_reader, data)
    return grouped_data


def find_band_data_files(path: Path, band_specs: BandSpecs):
    """
    Find band data files based on the given path and band specifications.

    Args:
        path (Path): The directory path to search for band data files.
        band_specs (BandSpecs): An instance of BandSpecs class containing the band indices.

    Returns:
        List[Tuple[Path, Path, Path]]: A list of tuples, where each tuple contains three Path objects representing
        the NIR, red, and green band files that match the given band specifications.
    """
    # find all NIR band files
    nir_band_files = [f for f in path.glob("*" + band_specs.nir_bidx + ".tif")]
    red_band_files = [f for f in path.glob("*" + band_specs.red_bidx + ".tif")]
    green_band_files = [f for f in path.glob("*" + band_specs.green_bidx + ".tif")]

    grouped_files: list[dict[str, Path]] = []
    for nir_f in nir_band_files:
        for red_f in red_band_files:
            for green_f in green_band_files:
                if (
                    nir_f.name.replace(band_specs.nir_bidx, band_specs.red_bidx)
                    == red_f.name
                    and nir_f.name.replace(band_specs.nir_bidx, band_specs.green_bidx)
                    == green_f.name
                ):
                    print(
                        f"Found files:\n  {nir_f.name}\n  {red_f.name}\n  {green_f.name}"
                    )
                    grouped = {"nir": nir_f, "red": red_f, "green": green_f}
                    grouped_files.append(grouped)

    return grouped_files


def main():
    bs = BandSpecs()
    print("Loaded band specs")
    band_files = find_band_data_files(DATA_PATH, bs)
    for grouped_files in band_files[:1]:
        processed_files = process_grouped_files(grouped_files, bs)

        nir_dataset_reader, nir_data = processed_files["nir"]
        red_dataset_reader, red_data = processed_files["red"]
        green_dataset_reader, green_data = processed_files["green"]

        mtvi2_data = calc_mtvi2(nir_data, green_data, red_data)
        print("here")

    pass


if __name__ == "__main__":
    main()


# order
# 1. Convert raw tiffs -> chl_a
# 2. Mask chl_a.tiffs to strawbs
