from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import rasterio
from sklearn.preprocessing import MinMaxScaler


# Function to load EVI data
def load_evi_data(file_path):
    with rasterio.open(file_path) as src:
        data = src.read(1)
        return data



def process_yield_data(yield_data_path:Path):

    # Load yield data
    yield_data = pd.read_csv(yield_data_path, parse_dates=['Date'], index_col='Date')

    # Check data
    print(yield_data.head())
    print("\nNumber of Yield Data Points: ", len(yield_data))
    print("\nColumn Names:", yield_data.columns)

    # Define the typical strawberry growing season as a temporal mask (so that we only consider when strawberries are being grown)
    def is_strawberry_season(date):
        return date.month in [3, 4, 5, 6, 7, 8, 9, 10]

    # Filter yield data to only include dates within the strawberry growing season
    yield_data = yield_data[yield_data.index.map(is_strawberry_season)]

    print("Number of Yield Data Points:", len(yield_data))

    # Resample yield data to weekly frequency
    yield_data_weekly = yield_data.resample('W').agg({
        'Volume (Pounds)': 'sum',
        'Cumulative Volumne (Pounds)': 'last',
        'Pounds/Acre': 'mean'
    })

    yield_data_weekly['Cumulative Volumne (Pounds)'] = yield_data_weekly['Cumulative Volumne (Pounds)'].ffill()
    yield_data_weekly['Cumulative Volumne (Pounds)'] = yield_data_weekly['Cumulative Volumne (Pounds)'].cummax()
    yield_data_weekly.fillna(0, inplace=True)

    # Add time features to yield data
    yield_data_weekly['month'] = yield_data_weekly.index.month
    yield_data_weekly['day_of_year'] = yield_data_weekly.index.dayofyear

    # Cyclical encoding for month
    yield_data_weekly['month_sin'] = np.sin(2 * np.pi * yield_data_weekly['month'] / 12)
    yield_data_weekly['month_cos'] = np.cos(2 * np.pi * yield_data_weekly['month'] / 12)

    # Cyclical encoding for day of year
    yield_data_weekly['day_of_year_sin'] = np.sin(2 * np.pi * yield_data_weekly['day_of_year'] / 365)
    yield_data_weekly['day_of_year_cos'] = np.cos(2 * np.pi * yield_data_weekly['day_of_year'] / 365)

    # Drop original time features
    yield_data_weekly.drop(['month', 'day_of_year'], axis=1, inplace=True)

    print("Yield data with time features:")
    print(yield_data_weekly.head())

    # Diego: TODO - Fix this... Scaling yield data at the start results in data leakage
    # This gives the model information about the test and validation sets by scaling all
    # records of the target variable.
    # Scaler should just fit_transform the training dataset 
    # and just transform the test/valid datasets
    # scaler should also be deployed with model

    scaler = MinMaxScaler()
    yield_data_weekly['Volume (Pounds)'] = scaler.fit_transform(yield_data_weekly[['Volume (Pounds)']])
    joblib.dump(scaler, "yield_scaler.save")

    return yield_data_weekly