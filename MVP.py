import streamlit as st
import folium
from streamlit_folium import folium_static
from folium.plugins import Draw, MiniMap
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64

# Initial setup
st.set_page_config(layout="wide")

# Initialize session state
if "view" not in st.session_state:
    st.session_state["view"] = "crop_health"
if "period" not in st.session_state:
    st.session_state["period"] = None
if "field_defined" not in st.session_state:
    st.session_state["field_defined"] = False
if "polygon_coordinates" not in st.session_state:
    st.session_state["polygon_coordinates"] = None
if 'expander_state' not in st.session_state:
    st.session_state['expander_state'] = {
        'field_of_interest': False,
        'period_of_interest': False,
        'vegetation_indices': False,
        'other_views': False
    }

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
    .banner { display: flex; justify-content: space-between; align-items: center; background-color: #024b30; height: 100px; padding: 15px; color: white; width: 100%; box-sizing: border-box; }
    .left-side { display: flex; align-items: center; }
    .banner img { width: 100px; margin-right: 20px; }
    .title { font-size: 2em; margin: 0; }
    .right-side { display: flex; align-items: center; }
    .dropdown { display: flex; align-items: center; margin-right: 10px; }
    .dropdown label { margin-right: 10px; }
    .dropdown select { background-color: #444444 !important; color: white !important; border: none; padding: 10px; border-radius: 4px; }
    .dropdown select:hover { background-color: #555555 !important; }
    .map-container { position: relative; width: 90%; height: 600px; margin: auto; }
    .coordinates { position: absolute; top: 10px; left: 10px; background: rgba(255, 255, 255, 0.8); padding: 5px; border-radius: 3px; font-size: 12px; }
    .color-legend { position: absolute; bottom: 50px; left: 10px; background: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 3px; }
    .color-legend div:hover { background-color: #dddddd; }
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

# Tooltip content for NDVI and EVI definitions - may not use
tooltip_ndvi = "Normalized Difference Vegetation Index (NDVI) is a measure of vegetation greenness."
tooltip_evi = "Enhanced Vegetation Index (EVI) is a measure of vegetation greenness that corrects for some atmospheric conditions and canopy background."

def create_tooltip(content):
    return f'<div class="tooltip">{content}<span>&#9432;</span><span class="tooltiptext">{content}</span></div>'

# Function to encode logo in base64
def get_base64_image(image_path):
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Path to logo
logo_path = "AgriSense_logo.png"

# Get the base64-encoded image
base64_image = get_base64_image(logo_path)

# Display the banner with logo, title, and dropdown
st.markdown(
    f"""
    <div class="banner">
        <div class="left-side">
            <img src="data:image/png;base64,{base64_image}" alt="AgriSense Logo">
            <h2 class="title">AgriSense</h2>
        </div>
        <div class="right-side">
            <div class="dropdown">
                <label for="view-select">Select View:</label>
                <select id="view-select" name="view">
                    <option value="crop_health">Crop Health</option>
                    <option value="yield_prediction">Yield Prediction</option>
                </select>
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

# View selection
view = st.selectbox("Select View:", ["Crop Health", "Yield Prediction"], key="view")

# Render content based on the selected view
if view == "Crop Health":

# Function to create the map
    def create_map():
        m = folium.Map(location=[36.7783, -119.4179], zoom_start=5) #CA Coordinates

        # Add draw tool
        draw = Draw(export=False)
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

    with st.sidebar.expander("🌍 Define Field of Interest"):
            st.write("Draw a polygon to define the field.")
            if st.button("Confirm Field"):
                st.session_state["field_defined"] = True

    with st.sidebar.expander("📅 Period of Interest"):
            period = st.radio("Select Period", options=["Single Day", "Multi-Day"], index=0 if st.session_state.get("period") is None else None)

            if period == "Single Day":
                selected_date = st.date_input("Select Date", st.session_state.get("selected_date", None))
                st.session_state["period"] = "Single Day"
                st.session_state["selected_date"] = selected_date
            elif period == "Multi-Day":
                start_date = st.date_input("Start Date", st.session_state.get("start_date", None))
                end_date = st.date_input("End Date", st.session_state.get("end_date", None))
                st.session_state["period"] = "Multi-Day"
                st.session_state["start_date"] = start_date
                st.session_state["end_date"] = end_date

    with st.sidebar.expander("🌱 Vegetation Indices"):
            st.write("Select an index to view:")

            if st.button("NDVI"):
                st.write(create_tooltip(tooltip_ndvi))

            if st.button("EVI"):
                st.write(create_tooltip(tooltip_evi))

    with st.sidebar.expander("🔍 Other Views"):
            if st.button("🌧️ Soil Moisture"):
                st.write("Displaying soil moisture...")

            if st.button("🌿 Chlorophyll Content"):
                st.write("Displaying chlorophyll content...")

            if st.button("☀️ Surface Temperature"):
                st.write("Displaying surface temperature...")

    if st.sidebar.button("🔄 Refresh"):
            message = st.sidebar.empty()
            message.write("Refreshing data...")
            time.sleep(3)
            message.empty()

    map_ = create_map()
    folium_static(map_, width=1025, height=475)

else:
    
    # Yield Prediction Plots
    def plot_yield_prediction():
    # Mock data for demonstration
        time_periods = pd.date_range(start='2020-01-01', periods=24, freq='M')
        actual_yield = np.random.randint(50, 150, size=len(time_periods))
        predicted_yield = actual_yield + np.random.randint(-20, 20, size=len(time_periods))
        compare_yield = actual_yield + np.random.randint(-30, 30, size=len(time_periods))

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(time_periods, actual_yield, label='Actual Yield', color='orange', linewidth=2)
        ax.plot(time_periods, predicted_yield, label='Predicted Yield', color='blue', linestyle='--', linewidth=2)
        ax.plot(time_periods, compare_yield, label='Compare Yield', color='green', linestyle='-.', linewidth=2)

        ax.set_xlabel("Time")
        ax.set_ylabel("Yield")
        ax.set_title("Yield Prediction Comparison")
        ax.legend()

        st.pyplot(fig)

    st.sidebar.title("Options")

    crop = st.sidebar.selectbox("Crop", ["Strawberries", "Blueberries", "Blackberries"])
    time_horizon = st.sidebar.selectbox("Time Horizon", ["Month", "Season", "Year"])
    time_units = st.sidebar.selectbox("Time Units", ["Days", "Months", "Years"])
    yield_units = st.sidebar.selectbox("Yield Units", ["Lbs", "Bushels"])
    period_to_predict = st.sidebar.selectbox("Period to Predict", [f"{y} {time_horizon}" for y in range(2019, 2025)])
    period_to_compare = st.sidebar.selectbox("Period to Compare", [f"{y} {time_horizon}" for y in range(2019, 2025)])

    if st.sidebar.button("Generate Graph"):
        message = st.sidebar.empty()
        message.write("Generating Graph...")
        time.sleep(3)
        message.empty()

    plot_yield_prediction()

