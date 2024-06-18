import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
from folium.plugins import Draw, MiniMap, MarkerCluster
import time

# Initialize the Streamlit app
st.set_page_config(layout="wide")

# Initialize session state 
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

# CSS for icon styling
st.markdown(
    """
    <style>
    .icon {
        font-size: 18px;
        margin-right: 10px;
        vertical-align: middle;
    }
    .dropdown-label {
        display: flex;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# CSS for the expander hover effect and down caret
st.markdown(
    """
    <style>
    .st-emotion-cache-13na8ym {
        background-color: inherit !important; /* Keep default background color */
    }
    .st-emotion-cache-p5msec:hover {
        background-color: #024b30 !important; /* Dark green hover background color */
        color: white !important; /* Optional: change text color on hover */
    }
    .st-emotion-cache-p5msec:hover svg {
        fill: white !important; /* Change caret color on hover */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# CSS for icons in options dropdown
st.markdown(
    """
    <style>
    .icon {
        font-size: 18px;
        margin-right: 10px;
        vertical-align: middle;
    }
    .dropdown-label {
        display: flex;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# CSS for the veg indices definitions tooltip
st.markdown(
    """
    <style>
    .tooltip {
        display: inline-flex;
        align-items: center;
        margin-left: 10px;
        position: relative;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #024b30;
        color: white;
        text-align: left;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 1;
        top: 0;
        left: 110%;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip span {
        font-size: 18px;
        cursor: pointer;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Tooltip content for NDVI and EVI definitions
tooltip_ndvi = "Normalized Difference Vegetation Index (NDVI) is a measure of vegetation greenness."
tooltip_evi = "Enhanced Vegetation Index (EVI) is a measure of vegetation greenness that corrects for some atmospheric conditions and canopy background."

# Function to create the tooltip HTML
def create_tooltip(content):
    return f'<div class="tooltip">{content}<span>&#9432;</span><span class="tooltiptext">{content}</span></div>'

# JavaScript to handle tooltips
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

# Display the JavaScript
st.markdown(script, unsafe_allow_html=True)

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
    <style>
    .banner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #024b30; /* Dark green */
        height: 100px;
        padding: 15px;
        color: white;
        width: 100%;
        box-sizing: border-box;
    }}
    .left-side {{
        display: flex;
        align-items: center;
    }}
    .banner img {{
        width: 100px; /* Adjust the width of the icon */
        margin-right: 20px; /* Add space between icon and text */
    }}    
    .title {{
        font-size: 2em; /* Adjust title size */
        margin: 0;
    }}
    .right-side {{
        display: flex;
        align-items: center;
    }}
    .dropdown {{
        display: flex;
        align-items: center;
        margin-right: 10px;
    }}
    .dropdown label {{
        margin-right: 10px;
    }}
    .dropdown select {{
        background-color: #444444 !important; /* Dark gray background */
        color: white !important; /* White text color */
        border: none;
        padding: 10px;
        border-radius: 4px;
    }}
    .dropdown select:hover {{
        background-color: #555555 !important; /* Slightly lighter dark gray on hover */
    }}
    </style>
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
    padding-top: 0rem;
    padding-bottom: 0rem;
    margin-top: 0rem;
}

</style>
""", unsafe_allow_html=True)

# Function to create the map
def create_map():
    # Center the map on CA
    m = folium.Map(location=[36.7783, -119.4179], zoom_start=5)  # Coordinates for California; zoom in 0.5 increments

    # Add draw tool
    draw = Draw(export=False)  # Disable export to prevent "ExportExportExport" issue
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

    # Add state lines (optional, you may need to adjust the GeoJSON path)
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

# Create the map
map_ = create_map()

# Display the map in Streamlit
folium_static(map_, width=1025, height=475)

# Collapsible panel
st.sidebar.title("Options")

# Expander for Define Field of Interest w icon
with st.sidebar.expander("🌍 Define Field of Interest"):
    st.write("Draw a polygon to define the field.")
    field_defined = False
    if st.button("Confirm Field"):
        field_defined = True

# Expander for Period of Interest w/ icon
with st.sidebar.expander("📅 Period of Interest"):
    # Radio buttons for period selection
    period = st.radio("Select Period", options=["Single Day", "Multi-Day"], index=0 if st.session_state["period"] is None else None)

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

    # Display the JavaScript
    st.markdown(script, unsafe_allow_html=True)

# Expander for Vegetation Indices
with st.sidebar.expander("🌱 Vegetation Indices"):
    st.write("Select an index to view:")

    # NDVI button with hover functionality
    if st.button("NDVI"):
        st.write(tooltip_ndvi)

    # EVI button with hover functionality
    if st.button("EVI"):
        st.write(tooltip_evi)

# Expander for Other Views
with st.sidebar.expander("🔍 Other Views"):
    # Button for Soil Moisture with icon
    if st.button("🌧️ Soil Moisture"):
        st.write("Displaying soil moisture...")

    # Button for Chlorophyll Content with icon
    if st.button("🌿 Chlorophyll Content"):
        st.write("Displaying chlorophyll content...")

    # Button for Surface Temperature with icon
    if st.button("☀️ Surface Temperature"):
        st.write("Displaying surface temperature...")

# Refresh button in the sidebar
if st.sidebar.button("🔄 Refresh"):
    # Show refreshing message
    message = st.sidebar.empty()  # Use st.sidebar.empty() to place the message in the sidebar
    message.write("Refreshing data...")

    # Simulate refresh delay 
    time.sleep(5)

    # Clear the message after delay
    message.empty()

# Main content area styling
map_container_style = """
    <style>
    .map-container {
        position: relative;
        width: 90%; /* Adjusted width */
        height: 600px;
        margin: auto; /* Center the map container */
    }
    .coordinates {
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(255, 255, 255, 0.8);
        padding: 5px;
        border-radius: 3px;
        font-size: 12px; /* Adjusted font size */
    }
    .color-legend {
        position: absolute;
        bottom: 50px;
        left: 10px;
        background: rgba(255, 255, 255, 0.8);
        padding: 10px;
        border-radius: 3px;
    }
    .color-legend div:hover {
        background-color: #dddddd; /* Adjust hover color as needed */
    }
    </style>
"""

st.markdown(map_container_style, unsafe_allow_html=True)

# Display the map and UI elements
st.markdown('<div class="map-container">', unsafe_allow_html=True)

# Display color legend on the map - need to get scale
if veg_index == "NDVI":
    st.markdown(
        """
        <div class="color-legend">
            <b>NDVI Legend</b><br>
            <div style='background-color: #024b30; width: 20px; height: 20px; display: inline-block;'></div> Low<br>
            <div style='background-color: #00ff00; width: 20px; height: 20px; display: inline-block;'></div> Medium<br>
            <div style='background-color: #0000ff; width: 20px; height: 20px; display: inline-block;'></div> High<br>
        </div>
        """,
        unsafe_allow_html=True
    )
elif veg_index == "EVI":
    st.markdown(
        """
        <div class="color-legend">
            <b>EVI Legend</b><br>
            <div style='background-color: #024b30; width: 20px; height: 20px; display: inline-block;'></div> Low<br>
            <div style='background-color: #00ff00; width: 20px; height: 20px; display: inline-block;'></div> Medium<br>
            <div style='background-color: #0000ff; width: 20px; height: 20px; display: inline-block;'></div> High<br>
        </div>
        """,
        unsafe_allow_html=True
    )

# End the map container div
st.markdown('</div>', unsafe_allow_html=True)
st.markdown(script, unsafe_allow_html=True)

