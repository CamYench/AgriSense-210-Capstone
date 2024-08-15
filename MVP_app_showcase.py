import streamlit as st
# Initial setup
st.set_page_config(layout="wide", page_title="AgriSense App (Beta)",page_icon="🌱")


import folium
from streamlit_folium import folium_static, st_folium
from folium.plugins import Draw, MiniMap
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import base64
import geopandas as gpd
import utm
from shapely.geometry import shape, Polygon, mapping
import plotly.express as px
import os

import torch

from concurrent.futures import ThreadPoolExecutor

# Import the model and functions from model_utils
from MVP_model_utils import CNNFeatureExtractor, HybridModel
from MVP_inference_utils import load_evi_data_and_prepare_features, predict_weekly_yield, load_masked_evi_and_prepare_features


#import image handler functions from landsat_handler
from landsat_handler import retrieve_latest_images, convert_selected_area, mask_tif

import joblib

scaler = joblib.load("./yield_scaler.save")

# Load weekly yield data
yield_data_weekly = pd.read_csv('yield_data_weekly.csv', index_col='Date')
yield_data_weekly.index = pd.to_datetime(yield_data_weekly.index)

#latest evi image location
evi_data_dir = './latest_masked_evi'



# Load the latest trained model
target_shape= (512,512)
model_path = 'trained-full-dataset.pt'

@st.cache_resource
def load_model():
    cnn_feature_extractor = CNNFeatureExtractor()
    model = HybridModel(cnn_feature_extractor)
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
    return model

# Usage
model = load_model()





# Initialize session state
if "view" not in st.session_state:
    st.session_state["view"] = "Crop Health"  
if "period" not in st.session_state:
    st.session_state["period"] = None
if "field_defined" not in st.session_state:
    st.session_state["field_defined"] = False
if "polygon_coordinates" not in st.session_state:
    st.session_state["polygon_coordinates"] = None
if "aoi" not in st.session_state:
    st.session_state["aoi"] = None
if "area" not in st.session_state:
    st.session_state["area"] = None
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = "Select an Option Below"
if 'message_shown' not in st.session_state:
    st.session_state.message_shown = False
if 'disable_selectbox_index' not in st.session_state:
    st.session_state.disable_selectbox_index = False
if 'disable_selectbox_other' not in st.session_state:
    st.session_state.disable_selectbox_other = False
if 'selectbox_other' not in st.session_state:
    st.session_state.selectbox_other = "Select an Option Below"
if 'refresh_message_shown' not in st.session_state:
    st.session_state.refresh_message_shown = False
if 'previous_aoi' not in st.session_state:
    st.session_state.previous_aoi = None
if 'evi_landsat' not in st.session_state:
    st.session_state['evi_landsat'] = None
if 'st_landsat' not in st.session_state:
    st.session_state['st_landsat'] = None
if 'smi_landsat' not in st.session_state:
    st.session_state['smi_landsat'] = None
if 'mtvi_landsat' not in st.session_state:
    st.session_state['mtvi_landsat'] = None
if 'evi_date' not in st.session_state:
    st.session_state['evi_date'] = None
if 'st_date' not in st.session_state:
    st.session_state['st_date'] = None
if 'smi_date' not in st.session_state:
    st.session_state['smi_date'] = None
if 'mtvi_date' not in st.session_state:
    st.session_state['mtvi_date'] = None
if 'model_prediction' not in st.session_state:
    st.session_state['model_prediction'] = None
if 'masked_date' not in st.session_state:
    st.session_state['masked_date'] = None

# CSS and JavaScript

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


script = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const tooltips = document.querySelectorAll('.tooltip');

    tooltips.forEach(tooltip => {
        const icon = tooltip.querySelector('span:nth-of-type(1)');
        const tooltipText = tooltip.querySelector('.tooltiptext');

        icon.addEventListener('mouseover', function() {
            tooltipText.style.visibility = 'visible';
            tooltipText.style.opacity = 1;
        });

        icon.addEventListener('mouseout', function() {
            tooltipText.style.visibility = 'hidden';
            tooltipText.style.opacity = 0;
        });
    });
});
</script>
"""

st.markdown(script, unsafe_allow_html=True)

def create_tooltip(content):
    return f'<div class="tooltip">{content}<span>&#9432;</span><span class="tooltiptext">{content}</span></div>'

# Function to encode logo in base64
def get_base64_image(image_path):
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Path to logo
logo_path = "AgriSenseLogo2.png"

# Get the base64-encoded image
base64_image = get_base64_image(logo_path)

# Display the banner with logo, title, and selectbox
st.markdown(
    f"""
    <div class="banner">
        <div class="left-side">
            <img src="data:image/png;base64,{base64_image}" alt="AgriSense Logo">
            <h2 class="title">AgriSense</h2>
        </div>
        <div class="right-side">
            <div class="dropdown">
        </div>
    """,
    unsafe_allow_html=True,
)

# Instruction text css to remove extra space
st.markdown(
    """
    <style>
    .instruction-text {
        margin-top: 0px; 
        font-size: 20px;
        margin-bottom: -70px; 
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the instruction text 
st.markdown('<p class="instruction-text">Make a selection below to view desired content:</p>', unsafe_allow_html=True)

# View selection
view = st.selectbox("View Selection", ["Crop Health", "Yield Prediction"], key="view", label_visibility="hidden")

# Close the HTML divs for the banner
st.markdown(
    """
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Remove space from above banner
st.markdown("""
<style>

.block-container
{
    padding-top: 2rem;
    padding-bottom: 0rem;
    margin-top: 0rem;
}

</style>
""", unsafe_allow_html=True)


def stream_data(input_text):
    # for word in input_text.split(" "):
    for letter in input_text:
        yield letter
        # yield word + " "
        time.sleep(0.02)


#get latest landsat file names
latest_file_names = os.listdir('./latest_display_images/')
latest_masked_file_names = os.listdir('./latest_masked_evi/')

# Constants for Landsat 8 TIRS band 10
L_MIN = 0.1  # Replace with metadata value
L_MAX = 22.0  # Replace with metadata value
QCAL_MIN = 1
QCAL_MAX = 65535

# Conversion constants for TIRS band 10 (specific to each scene, check MTL file)
K1 = 774.8853  # Thermal constant for band 10 (from MTL file)
K2 = 1321.0789  # Thermal constant for band 10 (from MTL file)

# Function to convert DN to Fahrenheit
def dn_to_fahrenheit(dn, l_min, l_max, qcal_min, qcal_max, k1, k2):
    radiance = l_min + (l_max - l_min) * (dn - qcal_min) / (qcal_max - qcal_min)
    kelvin = k2 / np.log((k1 / radiance) + 1)
    fahrenheit = ((kelvin - 273.15) * 9 / 5 + 32) - 50 #correction factor
    return fahrenheit

def find_files_with_sequence(file_list, sequence):
    """
    Find and return the file names in the given directory that contain the specified sequence of letters.

    :param file_list: list of strings object to search
    :param sequence: Sequence of letters to search for in file names
    :return: List of file names containing the sequence
    """
    matching_files = []

    # Iterate through the files in the directory
    for file_name in file_list:
        # Check if the sequence is in the file name
        if sequence in file_name:
            matching_files.append(file_name)

    matching_files.sort(reverse=True)
    return matching_files[0]

def calculate_area(geojson):
    try:

        # Handle the case where the GeoJSON object does not contain 'features'
        if "geometry" in geojson:
            geom = shape(geojson["geometry"])
        elif geojson and "features" in geojson:
            geom = shape(geojson["features"][0]["geometry"])
        else:
            st.write("Invalid GeoJSON structure.")
            return 0

        # Detect the appropriate UTM zone
        centroid = geom.centroid
        # st.write("Centroid:", centroid)
        utm_zone = utm.from_latlon(centroid.y, centroid.x)[2]
        is_northern = centroid.y >= 0
        crs = f"EPSG:{32600 + utm_zone if is_northern else 32700 + utm_zone}"
        # st.write("CRS:", crs)

        # Create a GeoDataFrame, project it to the UTM zone and calculate the area
        gdf = gpd.GeoDataFrame(index=[0], crs="EPSG:4326", geometry=[geom]) # type: ignore
        gdf = gdf.to_crs(crs)
        if not gdf.empty:
            gdf["area"] = gdf["geometry"].apply(lambda x: x.area)
        else:
            raise ValueError("GeoDataFrame is empty.")


        return gdf["area"].sum()
    except Exception as e:
        st.write(f"Exception occurred in calculate_area: {e}")
    return 0



# to speed up image processing
def process_images_in_parallel(aoi, file_paths):
    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda fp: mask_tif(aoi, fp), file_paths)
    return list(results)


# Render content based on the selected view
if view == "Crop Health":
# Function to create the map
    def create_map():
        m = folium.Map(location=[36.633, -121.545], zoom_start=11) #CA Coordinates

        # Add draw tool
        draw = Draw(
            export=False,             # Disables the export feature
            draw_options={
                'polyline': False,    # Disables drawing polylines
                'polygon': True,      # Enables drawing polygons
                'rectangle': False,    # Enables drawing rectangles
                'circle': False,      # Disables drawing circles
                'marker': False,        # Enables placing markers
                'circlemarker': False        # Enables placing markers
            },
            edit_options={
                'edit': False,        # Disables editing of drawn shapes
                'remove': False       # Disables removal of drawn shapes
            }
        )
        draw.add_to(m)

        # Add a Google Satellite layer
        tiles_url = "http://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
        folium.TileLayer(
            tiles=tiles_url,
            attr='Google',
            name='Google Satellite',
            overlay=True,
            control=True
        ).add_to(m)

        # Add a mini map with the normal Google Maps layer
        mini_map = MiniMap(tile_layer="OpenStreetMap", position="bottomright", width=150, height=150, zoom_level_offset=-4)
        m.add_child(mini_map)

        # Add mouseover event to update coordinates
        folium.LatLngPopup().add_to(m)

        # Add state lines
        state_geojson_url = 'https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json'
        folium.GeoJson(
            state_geojson_url,
            name='State Lines',
            style_function=lambda feature: {
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.1,
            }
        ).add_to(m)

        # Add major cities
        cities_data = [
            {"name": "Los Angeles", "location": [34.0522, -118.2437]},
            {"name": "San Francisco", "location": [37.7749, -122.4194]},
            {"name": "San Diego", "location": [32.7157, -117.1611]},
            {"name": "Sacramento", "location": [38.5816, -121.4944]},
            {"name": "Fresno", "location": [36.7372, -119.7871]},
        ]

        for city in cities_data:
            folium.Marker(
                location=city['location'],
                tooltip=city['name'],
                icon=folium.Icon(color='black', icon='map-marker')
            ).add_to(m)

        return m

    # Sidebar options
    st.sidebar.title("Options")

    
   # Initial options for the index and options selectboxes
    #options_index = ["Select an index", "NDVI", "EVI"]
    options_other = ["Select an Option Below", "🌱 EVI", "🌧️ Soil Moisture", "🌿 Chlorophyll Content", "☀️ Surface Temperature"]



    # Function to handle changes in selectbox other - Other
    def handle_selectbox_other_change():
        st.session_state.message_shown = True
        st.session_state.refresh_message_shown = False
        st.session_state.selected_option = st.session_state.selectbox_other
    if st.session_state.selectbox_other in ["🌱 EVI", "🌧️ Soil Moisture", "🌿 Chlorophyll Content", "☀️ Surface Temperature"]:
        st.session_state.disable_selectbox_index = True
    else:
        st.session_state.disable_selectbox_index = False



    # Selectbox Other with default value and options in the sidebar
    selectbox_other = st.sidebar.selectbox(
        "🔍 Field Views",
        options=options_other,
        index=options_other.index(st.session_state.selected_option),
        disabled=st.session_state.disable_selectbox_other,
        key='selectbox_other',
        on_change=handle_selectbox_other_change,
    )

    message = st.sidebar.empty()
    
    if st.session_state.selected_option != "Select an Option Below" and st.session_state.message_shown:
        message.write("Generating Satellite Data... It's worth the wait!")
        time.sleep(3)  # Simulate data generation delay (adjust as needed, not sure how long this will take)
        message.empty()  

        # Reset message_shown flag
        st.session_state.message_shown = False
    
    # if st.sidebar.button("🔄 Start Over"):
    #     message.write("Generating a blank slate...")
    #     time.sleep(3)
    #     message.empty()

        
    #     st.session_state.selected_option = "Select an Option Below"
    #     st.session_state.message_shown = False
    #     st.experimental_rerun()  # Rerun the app to reset the state



    map_ = create_map()

    with st.container():
        col1, col2 = st.columns([2,1])

        with col1:
            output = st_folium(map_, width=1025, height=475)
        with col2:
            if output and 'last_active_drawing' in output:
                if output['last_active_drawing'] == None:
                    st.subheader("Please select a target field area.")
                elif calculate_area(output['last_active_drawing']) >= 610000:
                    st.subheader("Please select an area smaller than 150 acres.")
                    st.session_state['aoi'] = None
                elif output['last_active_drawing'] == st.session_state['previous_aoi']:
                    #print calculated area converted to acres
                    area = round(st.session_state["area"]/4046.8564224,1)
                    area_str = str(area) + " acres"
                    # yield_str = str(int(round(st.session_state["model_prediction"] * area/79500,0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres
                    yield_str = str(int(round(st.session_state["model_prediction"],0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres

                    st.subheader("Calculated Area:")
                    st.write_stream(stream_data(area_str))
                    st.subheader("Predicted Yield:")
                    st.write_stream(stream_data(yield_str))
                else:

                    file_paths = [
                    './latest_display_images/' + find_files_with_sequence(latest_file_names, 'EVI'),
                    './latest_display_images/' + find_files_with_sequence(latest_file_names, 'ST'),
                    './latest_display_images/' + find_files_with_sequence(latest_file_names, 'SMI'),
                    './latest_display_images/' + find_files_with_sequence(latest_file_names, 'MTVI')
                    ]


                    latest_masked_fp = './latest_masked_evi/'+find_files_with_sequence(latest_masked_file_names,'masked')

                    masked_images = process_images_in_parallel(output['last_active_drawing'],file_paths)

                    st.session_state['evi_landsat'], st.session_state['st_landsat'], st.session_state['smi_landsat'], st.session_state['mtvi_landsat'] = masked_images

                    
                    st.session_state['evi_date'] = file_paths[0][41:49]
                    st.session_state['st_date'] = file_paths[1][41:49]
                    st.session_state['smi_date'] = file_paths[2][41:49]
                    st.session_state['mtvi_date'] = file_paths[3][41:49]

                    st.session_state['masked_date'] = latest_masked_fp[37:45]
                    
                    st.session_state['previous_aoi'] = st.session_state["aoi"]
                    st.session_state["aoi"] = output['last_active_drawing']
                    st.session_state["area"] = calculate_area(output['last_active_drawing'])
                        # st.write("Area of Interest (AOI) saved in session state.")
                
            


                    start_date = pd.to_datetime(st.session_state['masked_date']) # input date of latest EVI image

                    polygon_area_acres = st.session_state['area']/4046.8564224 # conversion to acres from square meters
                    # Load and preprocess the EVI data
                    time_index = [pd.to_datetime(time) for time in yield_data_weekly.index]

                    # evi_data_dict, time_features_list, mean, std = load_evi_data_and_prepare_features(evi_data_dir, time_index, target_shape)
                    # print([x.shape for x in evi_data_dict.values()])

     
                    evi_data_dict, time_features_list, mean, std = load_masked_evi_and_prepare_features(np.squeeze(mask_tif(output['last_active_drawing'],
                                                                                                                 file_paths[0],False)), st.session_state['evi_date'],
                                                                                                                 time_index, target_shape)

                    # Generate weekly predictions

                    
                    # create area modifier to scale historical yield data, this is portion of total strawberry growing area by acreage (9229 from latest cropscape)
                    area_modifier = st.session_state["area"]/4046.8564224/9229
                    # scale weekly yield data
                    yield_data_weekly_inf = yield_data_weekly.copy()
                    yield_data_weekly_inf['Volume (Pounds)'] = yield_data_weekly_inf['Volume (Pounds)'] * area_modifier
                    yield_data_weekly_inf['Cumulative Volumne (Pounds)'] = yield_data_weekly_inf['Cumulative Volumne (Pounds)'] * area_modifier
                    

                    device=None
                    # dates, predicted_yields = predict_weekly_yield(evi_data_dict, yield_data_weekly, start_date, polygon_area_acres, mean, std, target_shape, model, device)
                    dates, predicted_yields = predict_weekly_yield(evi_data_dict, yield_data_weekly_inf, start_date, polygon_area_acres, mean, std, target_shape, model, device)


                    # Convert predictions to a numpy array
                    predicted_yields = np.array(predicted_yields).flatten()
                    # st.session_state['model_prediction']=predicted_yields[0]/(512*512)
                    st.session_state['model_prediction']=scaler.inverse_transform((predicted_yields[0]/(512*512)).reshape(1,-1))[0][0] * area_modifier

                    if st.session_state["aoi"] == None:
                
                        pass
                    

                    else:

                        #print calculated area converted to acres
                        area = round(st.session_state["area"]/4046.8564224,1)
                        area_str = str(area) + " acres"

                        # yield_str = str(int(round(st.session_state["model_prediction"] * area/79500,0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres
                        yield_str = str(int(round(st.session_state["model_prediction"],0))) + " pounds of strawberries / week" #revamped for individual field prediction

                        st.subheader("Calculated Area:")
                        st.write_stream(stream_data(area_str))
                        st.subheader("Predicted Yield:")
                        st.write_stream(stream_data(yield_str))

                        # #TESTING ONLY!!!
                        # st.write(st.session_state["model_prediction"])
                        # st.write(predicted_yields)
                        # st.write(st.session_state['masked_date'])
                        # st.write (latest_masked_file_names)
                        # #TESTING ONLY!!!

                        # st.write("Calculated Area: " + str(round(st.session_state["area"]/4046.8564224,3)) + " acres")
                        # st.write("Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week")







    if st.session_state["aoi"] == None:
                
        pass

    elif calculate_area(output['last_active_drawing']) >= 610000:
        pass 

    else:

        with st.container():
            # st.markdown('<div class="output-container">', unsafe_allow_html=True)
            st.divider()
            # #print calculated area converted to acres
            # area = round(st.session_state["area"]/4046.8564224,1)
            # area_str = "Calculated Area: " + str(area) + " acres"
            # # yield_str = "Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week"
            # yield_str = "Predicted Yield: " + str(int(round(st.session_state["model_prediction"] * area/79500,0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres

            # st.write_stream(stream_data(area_str))
            # st.write_stream(stream_data(yield_str))

            # # st.write("Calculated Area: " + str(round(st.session_state["area"]/4046.8564224,3)) + " acres")
            # # st.write("Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week")

            if st.session_state.selected_option == "Select an Option Below":
                st.write("Please use '🔍 Field Views' option on the left to select a display metric!")

            elif st.session_state.selected_option == "🌱 EVI":
                    
                    # display expander to provide user with information about metric
                    with st.expander("What is Landsat Enhanced Vegitation Index (EVI)?"):
                        st.write('''
                            ##### Enhanced Vegetation Index (EVI)
                                 
                            EVI helps us understand how healthy and green vegetation is. It’s like a health check for plants! 🩺
                            
                            *Let’s get down in the weeds:*
                                 
                            EVI is a sophisticated vegetation index that provides insights into plant health. It 
                            outshines other vegetation indices like Normalized Difference Vegetation Index 
                            (NDVI) because it corrects for atmospheric conditions and canopy background noise 
                            so that it is more effective in areas of dense vegetation. Think of it as pruning away 
                            distractions! ✂️ 
                                 
                            *Digging into the technical details:*
                                 
                            EVI values range from -1 to 1, with scores between 0.2 and 0.8 indicating healthy 
                            vegetation. It works by combining and quantifying information gathered from blue 
                            (B2), red (B4), and near-infrared (B5) wavelengths to assess plant health. :rainbow:
                                 ''')
                        st.write('''
                            :nerd_face: If you want to get technical, the calculation from L1 Landsat data is: In Landsat 8-9,
EVI=2.5⋅(B5−B4)
(B5+6⋅B4−7.5⋅B2+1)
                                 ''')
                        st.write('''
                            :thought_balloon: Still curious? Check out our source: https://www.usgs.gov/landsat-missions/landsat-enhanced-vegetation-index
                                 ''')

                    evi_scale_factor = 0.0001 
                    #https://www.usgs.gov/landsat-missions/landsat-enhanced-vegetation-index?qt-science_support_page_related_con=0#qt-science_support_page_related_con
                    
                    # Mask the EVI values to include only those greater than -10001, the smallest valid value
                    mask = st.session_state['evi_landsat'][0] > -10001
                    masked_evi = np.where(mask, st.session_state['evi_landsat'][0]*evi_scale_factor, np.nan)
                    
                    #evi plot
                    fig = px.imshow(masked_evi, color_continuous_scale='YlGn', 
                                    title=f"Selected Field's EVI as of: {st.session_state['evi_date']}",
                                    width=1025, height=800)
                    #, range_color=[0,1]
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)
                    

                    #show figure in streamlit
                    st.plotly_chart(fig)

                    col1, col2, col3 = st.columns(3)
                    col1.metric('Average EVI Value:', round(np.nanmean(masked_evi),3))
                    col2.metric('Maximum EVI Value:', round(np.nanmax(masked_evi),3))
                    col3.metric('Minimum EVI Value:', round(np.nanmin(masked_evi),3))



                    flat_data_evi = masked_evi.flatten()
                    fig2 = px.histogram(flat_data_evi[~np.isnan(flat_data_evi)], nbins=50, title="Histogram of EVI",
                                        width=1025, height=500)
                    fig2.update_layout(xaxis_title="EVI", yaxis_title="Frequency", showlegend=False)
                    fig2.update_traces(marker_color='green', opacity=0.7)
                    st.plotly_chart(fig2)



            elif st.session_state.selected_option == "☀️ Surface Temperature":
                    


                    with st.expander("Why Surface Temperature?"):
                        st.write('''
                            ##### Surface Temperature:
                                 
                            Surface Temperature tells us how hot the Earth’s surface is, which can reveal crop 
                            stress due to heat. It’s like touching the ground to see if it's too hot for your plants! :fire:
                                 
                            *Let’s get down in the weeds:*
                                 
                            Surface Temperature is an important indicator of crop health, particularly when 
                            temperatures soar above 90-95°F. By measuring how hot the surface of the soil or 
                            crops is, you can better manage heat stress and ensure your plants stay cool under 
                            pressure. Think of it as giving your plants a temperature check! :thermometer:
                                 
                            *Digging into the technical details:*
                                 
                            Surface Temperature is measured using thermal infrared bands from satellites like 
                            Landsat. It ranges from -25°C to 45°C, depending on factors like sunlight and soil 
                            type. Ideal temperatures for most crops typically range from 15°C to 30°C (59°F to 
                            86°F). Within this range, crops generally thrive without excessive heat stress. 
                            Surface Temperature data helps in managing heat stress and optimizing crop 
                            conditions. :ear_of_rice:
                                 
                            :nerd_face: If you want to get technical, surface temperature data is obtained from Collection 
                            2 thermal infrared sensors, analyzing heat emitted by the Earth’s surface.
                                 ''')

                        st.write('''
                            :thought_balloon: Still curious? Check out our sources: https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature / https://climate.nasa.gov/news/3116/nasa-at-your-table-climate-change-and-its-environmental-impacts-on-crop-growth/
                                 ''')
                        

                    #convert to fahrenheit
                    st_landsat_f = dn_to_fahrenheit(st.session_state['st_landsat'][0], L_MIN, L_MAX, QCAL_MIN, QCAL_MAX, K1, K2)

                    # Mask the temperature values to include only those greater than 0 and less than 200
                    mask = (st_landsat_f > 0) & (st_landsat_f < 150)
                    masked_temp = np.where(mask, st_landsat_f, np.nan)

                    #surface temperature plot
                    fig = px.imshow(masked_temp, color_continuous_scale='Jet',
                                    title=f"Selected Field's Surface Temperature (°F) as of: {st.session_state['st_date']}",
                                    width=1025, height=800)
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)


                    
                    #show figure in streamlit
                    st.plotly_chart(fig)

                    col1, col2, col3 = st.columns(3)
                    col1.metric('Average Surface Temp (°F):', round(np.nanmean(masked_temp),1))
                    col2.metric('Maximum Surface Temp (°F):', round(np.nanmax(masked_temp),1))
                    col3.metric('Minimum Surface Temp (°F):', round(np.nanmin(masked_temp),1))


                    # histogram of presented data
                    flat_data = masked_temp.flatten()
                    fig2 = px.histogram(flat_data[~np.isnan(flat_data)], nbins=50, title="Histogram of Surface Temperature (°F)",
                                        width=1025, height=500)
                    fig2.update_layout(xaxis_title="Temperature (°F)", yaxis_title="Frequency", showlegend=False)
                    st.plotly_chart(fig2)
                    fig2.update_traces(marker_color='orange', opacity=0.7)

                    


            elif st.session_state.selected_option == "🌿 Chlorophyll Content":
                    
                    with st.expander("What does Chlorophyll Content (MTVI2) mean?"):
                        st.write('''
                            ##### Chlorophyll Content (MTVI2):
                                 
                            Chlorophyll Content readings are like a nutritional report for your plants, showing 
                            how well they are absorbing nutrients and how healthy they are. It’s your plant's 
                            way of letting you know if it's in tip-top shape or needs some help! :broccoli:
                                                            
                            *Let’s get down in the weeds:*    
                                                      
                            MTVI2 (Modified Triangular Vegetation Index) measures chlorophyll content to help 
                            optimize nutrient applications and detect plant stress. It’s effective in pinpointing 
                            issues like diseases, climate stress, or nutrient deficiencies. Think of it as keeping 
                            your plants' energy levels in check! :battery:
                                                            
                            *Digging into the technical details:*
                                 
                            Chlorophyll levels are assessed using satellite imagery, which measures how much 
                            light is absorbed and reflected by plants. Typically, values above 0.3-0.5 are 
                            considered good, but this can vary based on the crop and growth stage. High 
                            chlorophyll content typically indicates healthy plants, while lower levels may signal 
                            stress or disease. 🩺
                                                            
                            :nerd_face: If you want to get technical, MTVI2 calculations involve analyzing light reflectance 
                            in specific wavelengths to derive chlorophyll content.
                                 ''')
                        st.write('''
                            :thought_balloon: Still curious? Check out our sources: https://www.usgs.gov/landsat-missions/landsat-collection-2 / https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4366296/
                                 ''')

                    # Mask the MTVI2 values to include only those greater than 0
                    mask = st.session_state['mtvi_landsat'][0] > 0
                    masked_mtvi = np.where(mask, st.session_state['mtvi_landsat'][0], np.nan)
                    
                    #mtvi plot
                    fig = px.imshow(masked_mtvi, color_continuous_scale='YlGn', 
                                    title=f"Selected Field's Chlorophyll Content (MTVI2) as of: {st.session_state['mtvi_date']}",
                                    width=1025, height=800)
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)
                    

                    #show figure in streamlit
                    st.plotly_chart(fig)

                    col1, col2, col3 = st.columns(3)
                    col1.metric('Average MTVI2 Value:', round(np.nanmean(masked_mtvi),3))
                    col2.metric('Maximum MTVI2 Value:', round(np.nanmax(masked_mtvi),3))
                    col3.metric('Minimum MTVI2 Value:', round(np.nanmin(masked_mtvi),3))



                    flat_data_mtvi = masked_mtvi.flatten()
                    fig2 = px.histogram(flat_data_mtvi[~np.isnan(flat_data_mtvi)], nbins=50, title="Histogram of MTVI2",
                                        width=1025, height=500)
                    fig2.update_layout(xaxis_title="MTVI2", yaxis_title="Frequency", showlegend=False)
                    fig2.update_traces(marker_color='green', opacity=0.7)
                    st.plotly_chart(fig2)

                    


            elif st.session_state.selected_option == "🌧️ Soil Moisture":
                    
                    with st.expander("What is Soil Moisture Index (SMI)?"):
                        st.write('''
                            ##### Soil Moisture Index (SMI):
                                 
                            SMI helps us gauge how much water is in the soil, giving us a heads-up on crop 
                            watering needs. It’s like knowing when to water your plants before they get thirsty! :seedling:
                                 
                            *Let’s get down in the weeds:*
                                 
                            SMI is a crucial indicator that provides insights into soil moisture levels, helping you 
                            anticipate and manage unexpected dry periods. It ensures that no part of your field 
                            is neglected or losing moisture too quickly. Think of it as ensuring your plants 
                            always have a drink when they need it! :droplet:
                                 
                            *Digging into the technical details:*
                                 
                            SMI values vary, with higher values indicating more moisture in the soil. Specific 
                            thresholds can differ based on crop type and local conditions, but generally values 
                            above 0.3-0.5 are considered good. It is derived from satellite data, often using 
                            remote sensing techniques to measure soil moisture. Accurate SMI readings can 
                            help optimize irrigation and prevent water wastage. :satellite:
                                 ''')
                        st.write('''
                            :thought_balloon: Still curious? Check out our source: https://www.usgs.gov/landsat-missions/landsat-collection-2
                                 ''')


                    # Mask the soil moisture index (SMI) values to include only those greater than 0
                    mask = st.session_state['smi_landsat'][0] > 0
                    masked_smi = np.where(mask, st.session_state['smi_landsat'][0], np.nan)
                    
                    #smi plot
                    fig = px.imshow(masked_smi, color_continuous_scale='Blues', 
                                    title=f"Selected Field's SMI as of: {st.session_state['smi_date']}",
                                    width=1025, height=800)
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)
                    

                    #show figure in streamlit
                    st.plotly_chart(fig)

                    col1, col2, col3 = st.columns(3)
                    col1.metric('Average SMI Value:', round(np.nanmean(masked_smi),3))
                    col2.metric('Maximum SMI Value:', round(np.nanmax(masked_smi),3))
                    col3.metric('Minimum SMI Value:', round(np.nanmin(masked_smi),3))



                    flat_data_smi = masked_smi.flatten()
                    fig2 = px.histogram(flat_data_smi[~np.isnan(flat_data_smi)], nbins=50, title="Histogram of SMI",
                                        width=1025, height=500)
                    fig2.update_layout(xaxis_title="SMI", yaxis_title="Frequency", showlegend=False)
                    fig2.update_traces(marker_color='dodgerblue', opacity=0.7)
                    st.plotly_chart(fig2)

                    

            

            st.markdown('</div>', unsafe_allow_html=True)

    # st.write("Area of Interest (AOI):", st.session_state["aoi"])
    # st.write("Calculated Area:", st.session_state["area"], "square meters")



else:

    message = st.empty()

    if st.session_state["area"] is None or st.session_state['aoi'] is None:
        with message.container():
            st.write("Please return to the Crop Health view and select a valid field.")


    else: 
        message.empty()
    
        # Yield Prediction Plots
        def plot_yield_prediction():
        # Mock data for demonstration
            # time_periods = pd.date_range(start='2024-05-01', periods=8, freq='ME')
            # actual_yield = np.random.randint(50, 150, size=len(time_periods))
            # predicted_yield = actual_yield + np.random.randint(-20, 20, size=len(time_periods))
            # # compare_yield = actual_yield + np.random.randint(-30, 30, size=len(time_periods))

            #import actual data
            df = pd.read_csv('example_historical.csv')
            # df = pd.DataFrame({
            #     'Date': time_periods,
            #     'Actual Yield': actual_yield,
            #     'Predicted Yield': predicted_yield
            # })

            
            area = round(st.session_state["area"]/4046.8564224,1)

            #distribute yield by share of farm size
            df['actual_yield'] = df['actual_yield']*area/79500
            df['predicted_yield'] = df['predicted_yield']*area/79500

            df.rename(columns={'actual_yield': 'Actual Yield', 'predicted_yield': 'Predicted Yield'}, inplace=True)

            fig = px.line(df, x='date', y=['Actual Yield', 'Predicted Yield'],
              labels={'value': 'Yield', 'variable': 'Legend'},
              title='Strawberry Yields: Prediction vs Actual')

            fig.update_layout(
                xaxis_title='Time',
                yaxis_title='Yield (lbs of strawberries per week)',
                legend_title='',
                width=1000,
                height=600
            )


            st.plotly_chart(fig)




        st.sidebar.title("Options")

        # crop = st.sidebar.selectbox("🌱 Crop", ["Select a crop", "🍓 Strawberries", "🫐 Blueberries", "🍇 Grapes"])
        # time_horizon = st.sidebar.selectbox("⏳ Time Horizon", ["Select a time horizon", "🕰️ Month", "🍂 Season", "📆 Year"], help="The amount of time you wish to view on the graph.")
        # time_units = st.sidebar.selectbox("🕒 Time Units", ["Select a time unit", "📅 Days", "🕰️ Months", "📆 Years"], help="The units of time for the graph.")
        # yield_units = st.sidebar.selectbox("🎚️ Yield Units", ["Select a yield unit", "⚖️ Lbs", "🧺 Bushels"])

        # Placeholder text for the initial selectbox state
        placeholder_predict = "Select a period to predict"
        placeholder_compare = "Select a period to compare"

        # Dynamic options list
        # options = [f"{y} {time_horizon}" for y in range(2019, 2025)]

        # Selectbox widgets
        # period_to_predict = st.sidebar.selectbox("🔮 Period to Predict", [placeholder_predict] + options)
        # period_to_compare = st.sidebar.selectbox("📊 Period to Compare", [placeholder_compare] + options)

        if st.sidebar.button("Generate Graph"):
            message = st.sidebar.empty()
            message.write("Generating Graph...")
            time.sleep(3)
            message.empty()

        plot_yield_prediction()



st.divider()

home_url = 'http://www.agrisense.info'
st.markdown(f'''
<a href={home_url}><button style="background-color: white;color: Grey; border: 1px solid; border-radius: 12px;">AgriSense Home</button></a>
''',
unsafe_allow_html=True)

st.markdown('<div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)