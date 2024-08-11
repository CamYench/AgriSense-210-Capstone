import os
import time
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from skimage.draw import polygon
from skimage.transform import resize, rotate
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, median_absolute_error
from torch.utils.data import DataLoader, Dataset, Subset
from tqdm import tqdm
from utils import load_evi_data

METERS_PER_SQR_PX = 30 # 30m^2 per pixel

target_shape = (512, 512)

# Function to preprocess and normalize EVI data
def preprocess_image(image, target_shape, mean, std):
    image_resized = resize(image, target_shape, anti_aliasing=True)
    return (image_resized - mean) / std

def augment_image(image):
    # Apply random horizontal and vertical flips
    if np.random.rand() > 0.5:
        image = np.flipud(image)
    if np.random.rand() > 0.5:
        image = np.fliplr(image)
    # Apply random rotation
    angle = np.random.uniform(-45, 45)  # Rotate between -45 to 45 degrees
    image = rotate(image, angle, mode='reflect')
    # Apply random zoom
    zoom_factor = np.random.uniform(0.8, 1.2)
    image = resize(image, (int(image.shape[0] * zoom_factor), int(image.shape[1] * zoom_factor)), anti_aliasing=True)
    return image

# Function for unifying EVI and yield data
class CustomDataset(Dataset):
    def __init__(self, evi_data_dict, evi_reference, yield_data, sequence_length=4):
        self.evi_data_dict = evi_data_dict
        self.evi_reference = evi_reference
        self.yield_data = yield_data
        self.sequence_length = sequence_length

    def __len__(self):
        return len(self.yield_data) - self.sequence_length + 1

    def __getitem__(self, idx):
        evi_sequence = [self.evi_data_dict[self.evi_reference[idx + i]] for i in range(self.sequence_length)]
        evi_sequence = torch.tensor(evi_sequence, dtype=torch.float32).unsqueeze(1)
        yield_val = self.yield_data.iloc[idx + self.sequence_length - 1]['Volume (Pounds)']
        time_features = self.yield_data.iloc[idx + self.sequence_length - 1][['month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos']].values
        date = self.yield_data.iloc[idx + self.sequence_length -1].name.timestamp()
        return evi_sequence, torch.tensor(yield_val, dtype=torch.float32), torch.tensor(time_features, dtype=torch.float32), date
    
def sync_evi_yield_data(evi_data_dict, yield_data_weekly):
    evi_reference = []
    evi_data_dict_combined = {}

    for date in yield_data_weekly.index:
        # Find the closest available EVI date for each yield date
        closest_evi_date = find_closest_date(date, evi_data_dict)
        evi_reference.append(closest_evi_date)
        evi_data_dict_combined[closest_evi_date] = evi_data_dict[closest_evi_date]

    return evi_data_dict_combined, evi_reference
    
def prepare_dataset(evi_data_dir, yield_data_weekly, target_shape, augment=False, full=False):
    # Load EVI data
    evi_data_dict = {}
    evi_data_files = os.listdir(evi_data_dir)
    for idx, file in enumerate(evi_data_files):
        if file.endswith('.tiff'):
            tstart = time.perf_counter()
            date_str = os.path.basename(file).split('_')[3]
            date = pd.to_datetime(date_str, format='%Y%m%d')
            evi_data = load_evi_data(os.path.join(evi_data_dir, file))
            if augment:
                evi_data = augment_image(evi_data)
            evi_data_dict[date] = evi_data
            tend = time.perf_counter()
            duration = tend - tstart
            print(f"Processed file {idx+1}/{len(evi_data_files)} in {duration:.2f}s")

    # Extract mean and std from the preprocessed data
    mean, std = compute_mean_std(evi_data_dict, target_shape)

    # Preprocess all images using the calculated mean and std
    for date in evi_data_dict:
        evi_data_dict[date] = preprocess_image(evi_data_dict[date], target_shape, mean, std)

    # Determine common date range between EVI and yield data
    start_date, end_date = find_common_date_range(evi_data_dict, yield_data_weekly)

    # Filter yield_data_weekly to only include dates within the common range
    yield_data_weekly_filtered = yield_data_weekly[(yield_data_weekly.index >= start_date) & (yield_data_weekly.index <= end_date)]

    # Prepare dataset with synchronized EVI and yield data
    evi_data_dict_combined, evi_reference_combined = sync_evi_yield_data(evi_data_dict, yield_data_weekly_filtered)

    dataset = CustomDataset(evi_data_dict_combined, evi_reference_combined, yield_data_weekly_filtered)

    if full:
        train_loader = DataLoader(dataset, batch_size=4, shuffle=True)
        val_loader = None
    else:
        train_indices, val_indices = train_test_split(np.arange(len(dataset)), test_size=0.2, random_state=42)
        train_subset = torch.utils.data.Subset(dataset, train_indices)
        val_subset = torch.utils.data.Subset(dataset, val_indices)

        train_loader = DataLoader(train_subset, batch_size=4, shuffle=True)
        val_loader = DataLoader(val_subset, batch_size=4, shuffle=False)

    return train_loader, val_loader, mean, std, dataset

def train_and_evaluate(model, train_loader, val_loader, optimizer, scheduler, criterion, epochs, device):
    print(f"# of samples - Training   - {len(train_loader.dataset)}")
    print(f"# of samples - Validation - {len(val_loader.dataset)}")
    best_loss = float('inf')
    patience = 5
    trigger_times = 0
    target_shape = (512, 512)
    
    train_losses = []
    val_losses = []
    
    for epoch in range(epochs):
        running_loss = 0.0
        model.train()
        for inputs, labels, time_features, timestamp in tqdm(train_loader):
            inputs, labels, time_features = inputs.to(device), labels.to(device), time_features.to(device)
            optimizer.zero_grad()
            outputs = model(inputs, time_features)
            labels = labels / (target_shape[0] * target_shape[1])
            labels = labels.unsqueeze(1).unsqueeze(2).expand(-1, target_shape[0], target_shape[1])
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        
        epoch_loss = running_loss / len(train_loader)
        train_losses.append(epoch_loss)
        print(f'Epoch {epoch + 1}, Loss: {epoch_loss}')
        
        # Evaluate on validation set
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            all_outputs = []
            all_labels = []
            for inputs, labels, time_features, timestamps in val_loader:
                inputs, labels, time_features = inputs.to(device), labels.to(device), time_features.to(device)
                outputs = model(inputs, time_features)
                labels = labels.unsqueeze(1).unsqueeze(2).expand(-1, target_shape[0], target_shape[1])
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                
                all_outputs.extend(outputs.cpu().numpy().flatten())
                all_labels.extend(labels.cpu().numpy().flatten())

        val_loss /= len(val_loader)
        val_losses.append(val_loss)
        print(f'Validation Loss: {val_loss}')
        
        scheduler.step(val_loss)
        
        if val_loss < best_loss:
            best_loss = val_loss
            trigger_times = 0
        else:
            trigger_times += 1
            if trigger_times >= patience:
                print("Early stopping!")
                break
    
    # Compute final metrics for validation set
    all_outputs = np.array(all_outputs)
    all_labels = np.array(all_labels)
    
    val_mse = mean_squared_error(all_labels, all_outputs)
    val_rmse = np.sqrt(val_mse)
    val_mae = mean_absolute_error(all_labels, all_outputs)
    val_medae = median_absolute_error(all_labels, all_outputs)
    val_r2 = r2_score(all_labels, all_outputs)

    print(f"Final Validation Set Metrics - MSE: {val_mse}, RMSE: {val_rmse}, MAE: {val_mae}, MedAE: {val_medae}, R-squared: {val_r2}")

    return best_loss, train_losses, val_losses, val_mse, val_rmse, val_mae, val_medae, val_r2

# Function to find the mean & standard deviation
def compute_mean_std(evi_data_dict, target_shape):
    all_images = np.array([resize(image, target_shape, anti_aliasing=True) for image in evi_data_dict.values()])
    mean = np.mean(all_images)
    std = np.std(all_images)
    return mean, std

# Load EVI data and prepare time features
def load_evi_data_and_prepare_features(evi_data_dir, time_index, target_shape):
    
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
            time_features_list.append([0, 0, 0, 0])

    return evi_data_preprocessed_dict, time_features_list, mean, std

def find_closest_date(date, date_dict):
    closest_date = min(date_dict.keys(), key=lambda d: abs(d - date))
    return closest_date

def find_closest_date_in_df(date, df):
    closest_date = min(df.index, key=lambda d: abs(d - date))
    return closest_date

def find_common_date_range(evi_data_dict, yield_data_weekly):
    evi_dates = sorted(evi_data_dict.keys())
    yield_dates = sorted(yield_data_weekly.index)

    # Find the maximum of the minimum dates and the minimum of the maximum dates
    start_date = max(min(evi_dates), min(yield_dates))
    end_date = min(max(evi_dates), max(yield_dates))

    return start_date, end_date

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
        outputs = model(evi_data.unsqueeze(2), time_features) 
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
        time_features = yield_data_weekly.loc[closest_yield_date, ['month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos']].values
        
        predicted_yield_per_acre = predict(evi_data, time_features, mean, std, target_shape, model, device)
        
        predicted_yield_total = np.sum(predicted_yield_per_acre) * polygon_area
        predicted_yields.append(predicted_yield_total)
        dates.append(date_to_predict)
    
    return dates, predicted_yields