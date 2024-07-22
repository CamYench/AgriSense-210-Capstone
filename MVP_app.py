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

import torch

# Import the model and functions from model_utils
from model_utils import CNNFeatureExtractor, HybridModel, preprocess_input, predict_yield

#import image handler functions from landsat_handler
from landsat_handler import retrieve_latest_images, convert_selected_area, mask_tif

# Load the trained model
# model_path = 'train_model/best_hybrid_model.pth'

# cnn_feature_extractor = CNNFeatureExtractor()
# model = HybridModel(cnn_feature_extractor)
# model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
# model.eval() 

#get latest landsat



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

# CSS and JavaScript
st.markdown(
    """
    <style>
    .icon { font-size: 18px; margin-right: 10px; vertical-align: middle; }
    .dropdown-label { display: flex; align-items: center; }
    .st-emotion-cache-13na8ym { background-color: inherit !important; }
    .st-emotion-cache-p5msec:hover { background-color: #024b30 !important; color: white !important; }
    .st-emotion-cache-p5msec:hover svg { fill: white !important; }
    .tooltip { display: inline-flex; align-items: center; margin-left: 10px; position: relative; }
    .tooltip .tooltiptext { visibility: hidden; width: 200px; background-color: #024b30; color: white; text-align: left; border-radius: 6px; padding: 10px; position: absolute; z-index: 1; top: 0; left: 110%; opacity: 0; transition: opacity 0.3s; }
    .tooltip span { font-size: 18px; cursor: pointer; }
    .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
    .banner { display: flex; justify-content: space-between; align-items: center; background-color: #EAF7EE; height: 100px; padding: 15px; color: white; width: 100%; box-sizing: border-box; }
    .left-side { display: flex; align-items: center; }
    .banner img { width: 100px; margin-right: 20px; }
    .title { font-size: 2em; margin: 0; }
    .right-side { display: flex; align-items: center; }
    .dropdown { display: flex; align-items: center; margin-right: 10px; }
    .dropdown label { margin-right: 10px; }
    .dropdown select { background-color: #444444 !important; color: white !important; border: none; padding: 10px; border-radius: 4px; }
    .dropdown select:hover { background-color: #555555 !important; }
    .map-container { position: relative; width: 100%; height: 500px; margin: auto; }
    .coordinates { position: absolute; top: 10px; left: 10px; background: rgba(255, 255, 255, 0.8); padding: 5px; border-radius: 3px; font-size: 12px; }
    .color-legend { position: absolute; bottom: 50px; left: 10px; background: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 3px; }
    .color-legend div:hover { background-color: #dddddd; }
    iframe { height: 500px !important; }  /* Control the iframe height */
    .output-container { margin-bottom: 200px; }  /* Add padding under the output text */
    </style>
    """,
    unsafe_allow_html=True,
)
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
        st.write("Centroid:", centroid)
        utm_zone = utm.from_latlon(centroid.y, centroid.x)[2]
        is_northern = centroid.y >= 0
        crs = f"EPSG:{32600 + utm_zone if is_northern else 32700 + utm_zone}"
        st.write("CRS:", crs)

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
    options_other = ["Select an Option Below", "NDVI", "EVI", "🌧️ Soil Moisture", "🌿 Chlorophyll Content", "☀️ Surface Temperature"]



    # Function to handle changes in selectbox other - Other
    def handle_selectbox_other_change():
        st.session_state.message_shown = True
        st.session_state.refresh_message_shown = False
        st.session_state.selected_option = st.session_state.selectbox_other
    if st.session_state.selectbox_other in ["EVI", "NDVI", "🌧️ Soil Moisture", "🌿 Chlorophyll Content", "☀️ Surface Temperature"]:
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
        time.sleep(1)  # Simulate data generation delay (adjust as needed, not sure how long this will take)
        message.empty()  

        # Reset message_shown flag
        st.session_state.message_shown = False
    
    if st.sidebar.button("🔄 Refresh"):
        message.write("Refreshing data...")
        time.sleep(3)
        message.empty()

        st.session_state.selected_option = "Select an Option Below"
        st.session_state.message_shown = False
        st.experimental_rerun()  # Rerun the app to reset the state



    map_ = create_map()
    output = st_folium(map_, width=1025, height=475)






    # Save the last drawn GeoJSON to session state
    if output and 'last_active_drawing' in output:
        if output['last_active_drawing'] == None:
            st.write("Please select a target field area.")
        else:
            latest_file_names = retrieve_latest_images()
            evi_landsat = mask_tif(output['last_active_drawing'],latest_file_names[0])
            st_landsat = mask_tif(output['last_active_drawing'],latest_file_names[1])
            with st.container():
                st.markdown('<div class="output-container">', unsafe_allow_html=True)
                st.session_state["aoi"] = output['last_active_drawing']
                st.session_state["area"] = calculate_area(output['last_active_drawing'])
                # st.write("Area of Interest (AOI) saved in session state.")
                #print calculated area converted to acres
                st.write("Calculated Area:", round(st.session_state["area"]/4046.8564224,3), "acres")
                st.write("Predicted Yield:", round((st.session_state["area"]/4046.8564224) * 252.93856192,3), "pounds of strawberries / week")
            


                # # Define colormap and normalization
                # cmap = cm.viridis
                # norm_evi = mcolors.Normalize(vmin=0, vmax=np.max(evi_landsat[0]))
                # norm_st = mcolors.Normalize(vmin=0, vmax=np.max(st_landsat[0]))

                if st.session_state.selected_option == "Select an Option Below":
                    st.write("Please select metric to display!")

                elif st.session_state.selected_option == "EVI":
                
                    # Mask the EVI values to include only those greater than 0
                    mask = evi_landsat[0] > 0
                    masked_evi = np.where(mask, evi_landsat[0], np.nan)
                    
                    #evi plot
                    fig = px.imshow(masked_evi, color_continuous_scale='YlGn', 
                                    title=f"Selected Field's EVI as of: {latest_file_names[3]}",
                                    width=800, height=800)
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)
                    

                    #show figure in streamlit
                    st.plotly_chart(fig)


                    st.write(f'Maximum EVI Value: {np.nanmax(masked_evi)}')
                    st.write(f'Minimum EVI Value: {np.nanmin(masked_evi)}')


                    flat_data_evi = masked_evi.flatten()
                    fig2 = px.histogram(flat_data_evi[~np.isnan(flat_data_evi)], nbins=50, title="Histogram of EVI")
                    fig2.update_layout(xaxis_title="EVI", yaxis_title="Frequency", showlegend=False)
                    st.plotly_chart(fig2)

                elif st.session_state.selected_option == "☀️ Surface Temperature":
                    #convert to fahrenheit
                    st_landsat_f = dn_to_fahrenheit(st_landsat[0], L_MIN, L_MAX, QCAL_MIN, QCAL_MAX, K1, K2)

                    # Mask the temperature values to include only those greater than 0 and less than 200
                    mask = (st_landsat_f > 0) & (st_landsat_f < 200)
                    masked_temp = np.where(mask, st_landsat_f, np.nan)

                    #surface temperature plot
                    fig = px.imshow(masked_temp, color_continuous_scale='Jet', 
                                    title=f"Selected Field's Surface Temperature (°F) as of: {latest_file_names[3]}",
                                    width=800, height=800)
                    fig.update_coloraxes(colorbar_title_side="right")
                    fig.update_yaxes(visible=False, showticklabels=False)
                    fig.update_xaxes(visible=False, showticklabels=False)


                    
                    #show figure in streamlit
                    st.plotly_chart(fig)


                    st.write(f'Max Surface Temp: {np.nanmax(masked_temp)}')
                    st.write(f'Minimum Surface Temp: {np.nanmin(masked_temp)}')

                    # histogram of presented data
                    flat_data = masked_temp.flatten()
                    fig2 = px.histogram(flat_data[~np.isnan(flat_data)], nbins=50, title="Histogram of Surface Temperature (°F)")
                    fig2.update_layout(xaxis_title="Temperature (°F)", yaxis_title="Frequency", showlegend=False)
                    st.plotly_chart(fig2)




                elif st.session_state.selected_option == "🌿 Chlorophyll Content":
                    st.write(f"{st.session_state.selected_option} visualization coming soon!")
                elif st.session_state.selected_option == "🌧️ Soil Moisture":
                    st.write(f"{st.session_state.selected_option} visualization coming soon!")
                elif st.session_state.selected_option == "NDVI":
                    st.write(f"{st.session_state.selected_option} visualization coming soon!")

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

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(time_periods, actual_yield, label='Actual Yield', color='green', linewidth=2)
            ax.plot(time_periods, predicted_yield, label='Predicted Yield', color='lightblue', linestyle='--', linewidth=2)
            # ax.plot(time_periods, compare_yield, label='Compare Yield', color='green', linestyle='-.', linewidth=2)

            ax.set_xlabel("Time")
            ax.set_ylabel("Yield")
            ax.set_title("Yield Prediction Comparison")
            ax.legend()

            st.pyplot(fig)

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

