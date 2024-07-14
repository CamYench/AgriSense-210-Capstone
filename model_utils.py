import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from skimage.transform import resize

class CNNFeatureExtractor(nn.Module):
    def __init__(self):
        super(CNNFeatureExtractor, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.conv4 = nn.Conv2d(128, 256, 3, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.5)
        self.flattened_size = self._get_conv_output((1, 512, 512))

        self.fc1 = nn.Linear(self.flattened_size, 512)

    def _get_conv_output(self, shape):
        x = torch.rand(1, *shape)
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        x = self.pool(F.relu(self.bn4(self.conv4(x))))
        n_size = x.view(1, -1).size(1)
        return n_size

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        x = self.pool(F.relu(self.bn4(self.conv4(x))))
        x = self.dropout(x)
        x = x.view(-1, self.flattened_size)
        x = F.relu(self.fc1(x))
        return x

class HybridModel(nn.Module):
    def __init__(self, cnn_feature_extractor, lstm_hidden_size=64, lstm_layers=1):
        super(HybridModel, self).__init__()
        self.cnn = cnn_feature_extractor
        self.lstm = nn.LSTM(input_size=512, hidden_size=lstm_hidden_size, num_layers=lstm_layers, batch_first=True)
        self.fc1 = nn.Linear(lstm_hidden_size + 6, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x, time_features):
        batch_size, time_steps, C, H, W = x.size()
        c_in = x.view(batch_size * time_steps, C, H, W)
        c_out = self.cnn(c_in)
        r_in = c_out.view(batch_size, time_steps, -1)
        r_out, (h_n, c_n) = self.lstm(r_in)
        r_out = r_out[:, -1, :]
        x = torch.cat((r_out, time_features), dim=1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def preprocess_input(evi_data_dict, evi_reference, sequence_length=4):
    evi_sequence = []
    for i in range(sequence_length):
        evi_date = evi_reference[i]
        evi_sequence.append(evi_data_dict[evi_date])
    evi_sequence = np.array(evi_sequence)
    evi_sequence = torch.tensor(evi_sequence, dtype=torch.float32).unsqueeze(1)
    return evi_sequence

def predict_yield(model, evi_data_dict, evi_reference, yield_data, sequence_length=4):
    evi_sequence = preprocess_input(evi_data_dict, evi_reference, sequence_length)
    time_features = yield_data.iloc[-1][['month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos', 'Volume (Pounds)', 'Cumulative Volumne (Pounds)']].values
    time_features = torch.tensor(time_features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        prediction = model(evi_sequence.unsqueeze(0), time_features)
    return prediction.item()