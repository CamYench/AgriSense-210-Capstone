import streamlit as st
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

# Import the model and functions from model_utils
from MVP_model_utils import CNNFeatureExtractor, HybridModel
from MVP_inference_utils import load_evi_data_and_prepare_features, predict_weekly_yield


#import image handler functions from landsat_handler
from landsat_handler import retrieve_latest_images, convert_selected_area, mask_tif

# Load weekly yield data
yield_data_weekly = pd.read_csv('yield_data_weekly.csv', index_col='Date')
yield_data_weekly.index = pd.to_datetime(yield_data_weekly.index)

#latest evi image location
evi_data_dir = './latest_masked_evi'

# Load the latest trained model
target_shape= (512,512)
model_path = 'trained-full-dataset.pt'
cnn_feature_extractor = CNNFeatureExtractor()
model = HybridModel(cnn_feature_extractor)
model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
model.eval() 




# Initial setup
st.set_page_config(layout="wide")

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
    fahrenheit = (kelvin - 273.15) * 9 / 5 + 32
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
                elif output['last_active_drawing'] == st.session_state['previous_aoi']:
                    #print calculated area converted to acres
                    area = round(st.session_state["area"]/4046.8564224,1)
                    area_str = str(area) + " acres"
                    # yield_str = "Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week"
                    yield_str = str(int(round(st.session_state["model_prediction"] * area/79500,0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres
                    st.subheader("Calculated Area:")
                    st.write_stream(stream_data(area_str))
                    st.subheader("Predicted Yield:")
                    st.write_stream(stream_data(yield_str))
                else:
                    latest_evi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'EVI')
                    latest_st_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'ST')
                    latest_smi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'SMI')
                    latest_mtvi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'MTVI')


                    st.session_state['evi_landsat'] = mask_tif(output['last_active_drawing'],latest_evi_fp)
                    st.session_state['evi_date'] = latest_evi_fp[41:49]
                    st.session_state['st_landsat'] = mask_tif(output['last_active_drawing'],latest_st_fp)
                    st.session_state['st_date'] = latest_st_fp[41:49]
                    st.session_state['smi_landsat'] = mask_tif(output['last_active_drawing'],latest_smi_fp)
                    st.session_state['smi_date'] = latest_smi_fp[41:49]
                    st.session_state['mtvi_landsat'] = mask_tif(output['last_active_drawing'],latest_mtvi_fp)
                    st.session_state['mtvi_date'] = latest_mtvi_fp[41:49]
                    
                    st.session_state['previous_aoi'] = st.session_state["aoi"]
                    st.session_state["aoi"] = output['last_active_drawing']
                    st.session_state["area"] = calculate_area(output['last_active_drawing'])
                        # st.write("Area of Interest (AOI) saved in session state.")
                
                





                    start_date = pd.to_datetime(st.session_state['evi_date']) # input date of latest EVI image

                    polygon_area_acres = st.session_state['area']/4046.8564224 # conversion to acres from square meters
                    # Load and preprocess the EVI data
                    time_index = [pd.to_datetime(time) for time in yield_data_weekly.index]

                    evi_data_dict, time_features_list, mean, std = load_evi_data_and_prepare_features(evi_data_dir, time_index, target_shape)

                    # Generate weekly predictions
                    device=None
                    dates, predicted_yields = predict_weekly_yield(evi_data_dict, yield_data_weekly, start_date, polygon_area_acres, mean, std, target_shape, model, device)

                    # Convert predictions to a numpy array
                    predicted_yields = np.array(predicted_yields).flatten()
                    st.session_state['model_prediction']=predicted_yields[0]

                    if st.session_state["aoi"] == None:
                
                        pass

                    else:

                        #print calculated area converted to acres
                        area = round(st.session_state["area"]/4046.8564224,1)
                        area_str = str(area) + " acres"
                        # yield_str = "Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week"
                        yield_str = str(int(round(st.session_state["model_prediction"] * area/79500,0))) + " pounds of strawberries / week" #added fraction of 2023 cropscape strawberry acres
                        st.subheader("Calculated Area:")
                        st.write_stream(stream_data(area_str))
                        st.subheader("Predicted Yield:")
                        st.write_stream(stream_data(yield_str))

                        # st.write("Calculated Area: " + str(round(st.session_state["area"]/4046.8564224,3)) + " acres")
                        # st.write("Predicted Yield: " + str(int(round((st.session_state["area"]/4046.8564224) * 252.93856192,0))) + " pounds of strawberries / week")








    # # Save the last drawn GeoJSON to session state
    # if output and 'last_active_drawing' in output:
    #     if output['last_active_drawing'] == None:
    #         st.write("Please select a target field area.")
    #     elif output['last_active_drawing'] == st.session_state['previous_aoi']:
    #         pass
    #     else:
    #         latest_evi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'EVI')
    #         latest_st_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'ST')
    #         latest_smi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'SMI')
    #         latest_mtvi_fp = './latest_display_images/'+find_files_with_sequence(latest_file_names,'MTVI')


    #         st.session_state['evi_landsat'] = mask_tif(output['last_active_drawing'],latest_evi_fp)
    #         st.session_state['evi_date'] = latest_evi_fp[41:49]
    #         st.session_state['st_landsat'] = mask_tif(output['last_active_drawing'],latest_st_fp)
    #         st.session_state['st_date'] = latest_st_fp[41:49]
    #         st.session_state['smi_landsat'] = mask_tif(output['last_active_drawing'],latest_smi_fp)
    #         st.session_state['smi_date'] = latest_smi_fp[41:49]
    #         st.session_state['mtvi_landsat'] = mask_tif(output['last_active_drawing'],latest_mtvi_fp)
    #         st.session_state['mtvi_date'] = latest_mtvi_fp[41:49]
            
    #         st.session_state['previous_aoi'] = st.session_state["aoi"]
    #         st.session_state["aoi"] = output['last_active_drawing']
    #         st.session_state["area"] = calculate_area(output['last_active_drawing'])
    #             # st.write("Area of Interest (AOI) saved in session state.")
                
                





    #         start_date = pd.to_datetime(st.session_state['evi_date']) # input date of latest EVI image

    #         polygon_area_acres = st.session_state['area']/4046.8564224 # conversion to acres from square meters
    #         # Load and preprocess the EVI data
    #         time_index = [pd.to_datetime(time) for time in yield_data_weekly.index]

    #         evi_data_dict, time_features_list, mean, std = load_evi_data_and_prepare_features(evi_data_dir, time_index, target_shape)

    #         # Generate weekly predictions
    #         device=None
    #         dates, predicted_yields = predict_weekly_yield(evi_data_dict, yield_data_weekly, start_date, polygon_area_acres, mean, std, target_shape, model, device)

    #         # Convert predictions to a numpy array
    #         predicted_yields = np.array(predicted_yields).flatten()
    #         st.session_state['model_prediction']=predicted_yields[0]




    if st.session_state["aoi"] == None:
                
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
                            Enhanced Vegetation Index is a way to quantify vegetation greenness, but is differentiated from other methods by correcting
                                 for atmospheric conditions and canopy background noise.  
                                 The value ranges from -1 to 1, with values between 0.2 and 0.8 indicating healthy vegetation.
                                 ''')
                        st.write('''
                            If you want to get technical, the calculation from L1 Landsat data is: In Landsat 8-9, EVI = 2.5 * ((Band 5 – Band 4) / (Band 5 + 6 * Band 4 – 7.5 * Band 2 + 1))
                                 
                                 ''')
                        st.write('''
                            To know more, visit our source: https://www.usgs.gov/landsat-missions/landsat-enhanced-vegetation-index
                                 ''')

                    evi_scale_factor = 0.0001 
                    #https://www.usgs.gov/landsat-missions/landsat-enhanced-vegetation-index?qt-science_support_page_related_con=0#qt-science_support_page_related_con
                    
                    # Mask the EVI values to include only those greater than 0
                    mask = st.session_state['evi_landsat'][0] > 0
                    masked_evi = np.where(mask, st.session_state['evi_landsat'][0]*evi_scale_factor, np.nan)
                    
                    #evi plot
                    fig = px.imshow(masked_evi, color_continuous_scale='YlGn', 
                                    title=f"Selected Field's EVI as of: {st.session_state['evi_date']}",
                                    width=1025, height=800)
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
                            Surface Temperature can be an important indicator of crop stress.
                                 ''')
                        st.write('''
                            We get surface temperature using Landsat Collection 2 thermal infrared bands.
                                 
                                 ''')
                        st.write('''
                            To know more, visit our source: [link]https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature
                                 ''')
                        

                    #convert to fahrenheit
                    st_landsat_f = dn_to_fahrenheit(st.session_state['st_landsat'][0], L_MIN, L_MAX, QCAL_MIN, QCAL_MAX, K1, K2)

                    # Mask the temperature values to include only those greater than 0 and less than 200
                    mask = (st_landsat_f > 0) & (st_landsat_f < 200)
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
                            Chlorophyll Content readings can enable customized nutrient applications and optimal crop nutrition.
                                 ''')
                        st.write('''
                            The way Chlorophyll content....
                                 
                                 ''')
                        st.write('''
                            To know more, visit our source: [link]https://www.usgs.gov/landsat-missions/landsat-collection-2
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
                            SMI gives an indication of crop watering needs and lets you get ahead of unexpected dry period impacts.
                                 ''')
                        st.write('''
                            Calculating SMI....
                                 
                                 ''')
                        st.write('''
                            To know more, visit our source: [link]https://www.usgs.gov/landsat-missions/landsat-collection-2
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

    if st.session_state["aoi"] is None:
        with message.container():
            st.write("Please return to the Crop Health view and select a field.")

    else: 
        message.empty()
    
        # Yield Prediction Plots
        def plot_yield_prediction():
        # Mock data for demonstration
            time_periods = pd.date_range(start='2024-01-01', periods=13, freq='ME')
            actual_yield = np.random.randint(50, 150, size=len(time_periods))
            predicted_yield = actual_yield + np.random.randint(-20, 20, size=len(time_periods))
            # compare_yield = actual_yield + np.random.randint(-30, 30, size=len(time_periods))


            df = pd.DataFrame({
                'Date': time_periods,
                'Actual Yield': actual_yield,
                'Predicted Yield': predicted_yield
            })
            fig = px.line(df, x='Date', y=['Actual Yield', 'Predicted Yield'],
              labels={'value': 'Yield', 'variable': 'Legend'},
              title='Yield Prediction Comparison')

            fig.update_layout(
                xaxis_title='Time',
                yaxis_title='Yield',
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