import os
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
from skimage.draw import polygon
from skimage.transform import resize, rotate
from utils import load_evi_data

METERS_PER_SQR_PX = 30 # 30m^2 per pixel


# Function to preprocess and normalize EVI data
def preprocess_image(image, target_shape, mean, std):
    image_resized = resize(image, target_shape, anti_aliasing=True)
    return (image_resized - mean) / std

# Fucntion to find the mean & standard deviation
def compute_mean_std(evi_data_dict, target_shape):
    all_images = np.array([resize(image, target_shape, anti_aliasing=True) for image in evi_data_dict.values()])
    mean = np.mean(all_images)
    std = np.std(all_images)
    return mean, std

# Load EVI data and prepare time features
def load_evi_data_and_prepare_features(evi_data_dir, time_index, target_shape):
    
    # why are we loading in every evi data file for inference?
    evi_data_dict = {}
    for file in os.listdir(evi_data_dir):
        if file.endswith('.tiff'):
            date_str = os.path.basename(file).split('_')[3]
            date = pd.to_datetime(date_str, format='%Y%m%d')
            evi_data = load_evi_data(os.path.join(evi_data_dir, file))
            evi_data_dict[date] = evi_data

    mean, std = compute_mean_std(evi_data_dict, target_shape)

    # Prepare features
    evi_data_preprocessed_dict = {}
    time_features_list = []
    for date in time_index:
        if date in evi_data_dict:
            evi_data = evi_data_dict[date]
            month_sin = np.sin(2 * np.pi * date.month / 12)
            month_cos = np.cos(2 * np.pi * date.month / 12)
            day_of_year_sin = np.sin(2 * np.pi * date.day_of_year / 365)
            day_of_year_cos = np.cos(2 * np.pi * date.day_of_year / 365)
            time_features = [month_sin, month_cos, day_of_year_sin, day_of_year_cos]
            evi_data_preprocessed = preprocess_image(evi_data, target_shape, mean, std)
            evi_data_preprocessed_dict[date] = evi_data_preprocessed
            time_features_list.append(time_features)
        else:
            time_features_list.append([0, 0, 0, 0])  # Placeholder for missing data

    return evi_data_preprocessed_dict, time_features_list, mean, std

def find_closest_date(date, date_dict):
    closest_date = min(date_dict.keys(), key=lambda d: abs(d - date))
    return closest_date

def find_closest_date_in_df(date, df):
    closest_date = min(df.index, key=lambda d: abs(d - date))
    return closest_date

def mask_evi_data(evi_data, polygon_coords):
    mask = np.zeros_like(evi_data)
    rr, cc = polygon(polygon_coords[:, 0], polygon_coords[:, 1], mask.shape)
    mask[rr, cc] = 1
    return mask

def predict(evi_data, time_features, mean, std, target_shape, model, device):
    model.eval()
    evi_data = preprocess_image(evi_data, target_shape, mean, std)
    evi_data = torch.tensor(evi_data, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
    time_features = torch.tensor(time_features, dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(evi_data.unsqueeze(2), time_features)  # Add a dimension for time_steps
    return outputs.cpu().numpy()

def predict_weekly_yield(evi_data_dict, yield_data_weekly, start_date, polygon_area, mean, std, target_shape, model, device):
    model.eval()
    predicted_yields = []
    dates = []
    
    for week_offset in range(13):  # 13 weeks for 3 months
        date_to_predict = start_date + timedelta(weeks=week_offset)
        
        closest_evi_date = find_closest_date(date_to_predict, evi_data_dict)
        closest_yield_date = find_closest_date_in_df(date_to_predict, yield_data_weekly)
        
        evi_data = evi_data_dict[closest_evi_date]
        time_features = yield_data_weekly.loc[closest_yield_date, ['month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos', 'Volume (Pounds)', 'Cumulative Volumne (Pounds)']].values
        
        predicted_yield_per_acre = predict(evi_data, time_features, mean, std, target_shape, model, device)
        
        predicted_yield_total = np.sum(predicted_yield_per_acre) * polygon_area
        predicted_yields.append(predicted_yield_total)
        dates.append(date_to_predict)
    
    return dates, predicted_yields