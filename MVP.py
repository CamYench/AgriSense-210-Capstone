import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
from folium.plugins import Draw, MiniMap

# Initialize the Streamlit app
st.set_page_config(layout="wide")

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

# Top banner with dropdown and logo
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
    }}
    .banner img {{
        width: 100px; /* Adjust the width of the icon */
        margin-right: 20px; /* Add space between icon and text */
        margin-left: 0px;
    }}    
    .dropdown {{
        margin-left: 350px;
    }}
    .dropdown select {{
        background-color: #444444 !important; /* Dark gray background */
        color: white !important; /* White text color */
        border: none;
        padding: 11px;
        border-radius: 4px;
    }}
    .dropdown select:hover {{
        background-color: #444444 !important; /* Keep the same dark gray background on hover */
    }}
    .refresh-button {{
        background: #444444;
        padding: 8px;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        font-size: 16px; /* Adjusted font size */
        margin-left: auto; /* Push refresh button to the right */
    }}
    .refresh-button:hover {{
        background-color: #cccccc; /* Adjust hover color as needed */
    }}    
    </style>
    <div class="banner">
        <img src="data:image/png;base64,{base64_image}" alt="AgriSense Logo">
        <h2>AgriSense</h2>
        <div class="dropdown">
            <label for="view-select">Select View:</label>
            <select id="view-select" name="view">
                <option value="crop_health">Crop Health</option>
                <option value="yield_prediction">Yield Prediction</option>
            </select>
        </div>
        <button class="refresh-button" onclick="window.location.reload();">Refresh 🔄</button>
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
    m = folium.Map(location=[36.7783, -119.4179], zoom_start=6)  # Coordinates for California

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
    mini_map = MiniMap(tile_layer="OpenStreetMap", position="bottomright", width=150, height=150, zoom_level_offset=-8)
    m.add_child(mini_map)

    # Add mouseover event to update coordinates
    folium.LatLngPopup().add_to(m)

    return m

# Create the map
map_ = create_map()

# Display the map in Streamlit
folium_static(map_)

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
    period_selection = st.empty()
    
    # Display the initial selection interface
    period_selection.markdown("""
    <label style="display: block; margin-bottom: 10px;"><input type="radio" name="period" value="Single Day"> Single Day</label>
    <label style="display: block;"><input type="radio" name="period" value="Multi-Day"> Multi-Day</label>
    """, unsafe_allow_html=True)

    # Handle date inputs based on user selection
    if "period" in st.session_state:
        if st.session_state["period"] == "Single Day":
            selected_date = st.date_input("Select Date")
            st.session_state["selected_date"] = selected_date
        elif st.session_state["period"] == "Multi-Day":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            st.session_state["start_date"] = start_date
            st.session_state["end_date"] = end_date

    # JavaScript to handle period selection
    script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const radios = document.querySelectorAll('input[type="radio"][name="period"]');
        radios.forEach(radio => {
            radio.addEventListener('change', function() {
                const selectedPeriod = this.value;
                const form = this.closest('form');
                const data = new FormData(form);
                const value = Object.fromEntries(data.entries());
                const output = JSON.stringify(value);

                const command = {
                    type: 'update',
                    data: output,
                };

                // Send the command to Streamlit
                if (Streamlit.connection) {
                    Streamlit.connection.send(command);
                }
            });
        });
    });
    </script>
    """

    # Display the JavaScript
    st.markdown(script, unsafe_allow_html=True)

# JavaScript to reload the page
reload_script = """
<script>
function refreshPage() {
    window.location.reload();
}
</script>
"""

# Expander for veg indices
with st.sidebar.expander("🌱 Vegetation Indices"):
    st.write("Select an index to view:")
    
    # NDVI radio button with tooltip
    st.markdown(f'<label><input type="radio" name="index" value="NDVI"> NDVI <span class="tooltip"><span>&#9432;</span><span class="tooltiptext">{tooltip_ndvi}</span></span></label>', unsafe_allow_html=True)
    
    # EVI radio button with tooltip
    st.markdown(f'<label><input type="radio" name="index" value="EVI"> EVI <span class="tooltip"><span>&#9432;</span><span class="tooltiptext">{tooltip_evi}</span></span></label>', unsafe_allow_html=True)

# Expander for Soil Moisture with icon
with st.sidebar.expander("🌧️ Soil Moisture"):
    st.write("Soil moisture options here...")

# Expander for Chlorophyll Content with icon
with st.sidebar.expander("🌿 Chlorophyll Content"):
    st.write("Chlorophyll content options here...")

# Expander for Surface Temperature w icon
with st.sidebar.expander("☀️ Surface Temperature"):
    st.write("Surface temperature options here...")

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
