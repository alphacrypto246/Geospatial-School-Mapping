import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point

# Title and description
st.title("Geospatial School Mapping - Tamil Nadu")
st.markdown("""
This application visualizes schools in Tamil Nadu and provides insights such as:
- School locations
- Flood Risk Dashboard
- Access analysis
- Hazard-prone schools
- Weather & Cyclone Status
""")

# Load data
@st.cache_data
def load_data():
    # Load Tamil Nadu boundaries
    tamil_nadu_map = gpd.read_file("tamil_nadu.geojson")
    
    # Load school data
    schools = pd.read_csv("schools.csv")
    geometry = [Point(xy) for xy in zip(schools['longitude'], schools['latitude'])]
    schools_gdf = gpd.GeoDataFrame(schools, geometry=geometry, crs="EPSG:4326")
    
    # Load hazard zones
    hazard_zones = gpd.read_file("hazards.geojson")
    
    return tamil_nadu_map, schools_gdf, hazard_zones

# Load cached data
tamil_nadu_map, schools_gdf, hazard_zones = load_data()

# User selection for analysis
analysis_type = st.sidebar.selectbox(
    "Select Analysis Type",
    ["Flood Risk Dashboard", "View Schools", "Access Analysis", "Hazard Analysis", "Weather & Cyclone Status"]
)

# Base map
m = folium.Map(location=[14, 81], zoom_start=7)  # Centered on Tamil Nadu

# View Schools
if analysis_type == "View Schools":
    st.subheader("School Locations in Tamil Nadu")
    for _, row in schools_gdf.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=row['name'],
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
    folium.GeoJson(tamil_nadu_map, name="Tamil Nadu").add_to(m)
    st_folium(m, width=700, height=500)
    st.write("Schools & Universities")
    st.write(schools_gdf)

# Flood Risk Dashboard
elif analysis_type == "Flood Risk Dashboard":
    st.subheader("Flood Risk Dashboard")
    # Sample dataset
    data = {
        "City": ["Chennai", "Madurai", "Coimbatore", "Trichy"],
        "Lat": [13.0827, 9.9252, 11.0168, 10.7905],
        "Lon": [80.2707, 78.1198, 76.9558, 78.7047],
        "Rainfall": [210, 120, 95, 160],
        "Elevation": [6, 101, 411, 88],
        "RiverDist": [1.2, 3.5, 6.0, 2.1]
    }

    df = pd.DataFrame(data)

    # Risk score calculation
    def risk_score(row):
        score = (
            row["Rainfall"] * 0.03 +
            max(0, 200 - row["Elevation"]) * 0.02 +
            max(0, 5 - row["RiverDist"]) * 0.5
        )
        return score

    df["RiskScore"] = df.apply(risk_score, axis=1)

    # Classification
    def classify(score):
        if score > 7:
            return "Severe"
        elif score > 5:
            return "Moderate"
        elif score > 3:
            return "Watch"
        else:
            return "Low"

    df["RiskLevel"] = df["RiskScore"].apply(classify)

    # Stats panel
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Cities", len(df))
    col2.metric("Severe Risk", (df["RiskLevel"] == "Severe").sum())
    col3.metric("Moderate Risk", (df["RiskLevel"] == "Moderate").sum())
    col4.metric("Low Risk", (df["RiskLevel"] == "Low").sum())

    # Map
    m = folium.Map(location=[11.0, 78.5], zoom_start=7)

    colors = {
        "Severe": "red",
        "Moderate": "orange",
        "Watch": "yellow",
        "Low": "green"
    }

    for _, row in df.iterrows():

        popup = f"""
        <b>{row['City']}</b><br>
        Rainfall: {row['Rainfall']} mm<br>
        Elevation: {row['Elevation']} m<br>
        River Distance: {row['RiverDist']} km<br>
        Risk Level: {row['RiskLevel']}<br>
        Score: {round(row['RiskScore'],2)}
        """

        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=row["Rainfall"] / 15,  # size based on rainfall
            popup=popup,
            color=colors[row["RiskLevel"]],
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    st_folium(m, width=1100, height=600)

    # District summary table
    st.subheader("City Risk Summary")
    st.dataframe(df[["City", "Rainfall", "RiskLevel"]])

# Access Analysis section (replace the existing section)
elif analysis_type == "Access Analysis":
    st.subheader("Access Analysis")
    user_lat = st.number_input("Enter Latitude", value=12.8239)
    user_lon = st.number_input("Enter Longitude", value=80.0450)
    max_distance_km = st.slider("Select Maximum Distance (in km)", 1, 100, 5)

    # Buffer user's location and find nearby schools
    user_point = Point(user_lon, user_lat)
    user_gdf = gpd.GeoDataFrame(geometry=[user_point], crs="EPSG:4326")
    buffer = user_gdf.buffer(max_distance_km / 111)  # Convert km to degrees
    nearby_schools = schools_gdf[schools_gdf.geometry.within(buffer.iloc[0])]

    # Map and results
    folium.Marker(
        location=[user_lat, user_lon], 
        popup="Your Location", 
        icon=folium.Icon(color="red", icon="home")  # Changed to red icon
    ).add_to(m)
    
    for _, row in nearby_schools.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=row['name'],
            icon=folium.Icon(color="green", icon="info-sign")
        ).add_to(m)
    
    folium.GeoJson(tamil_nadu_map, name="Tamil Nadu").add_to(m)
    st_folium(m, width=700, height=500)
    st.write("Nearby Schools:")
    st.write(nearby_schools[['name', 'latitude', 'longitude']])
    
# Hazard Analysis
elif analysis_type == "Hazard Analysis":
    st.subheader("Hazard Analysis")
    buffer_distance_km = st.slider("Buffer Distance Around Hazard Zones (in km)", 1, 100, 5)

    # Buffer hazard zones
    hazard_zones_buffered = hazard_zones.to_crs(epsg=3395).buffer(buffer_distance_km * 1000).to_crs(epsg=4326)

    # Schools in hazard zones
    schools_in_hazard = gpd.sjoin(schools_gdf, hazard_zones, how="inner")

    # Schools around hazard zones (in buffer)
    hazard_zones_buffered_gdf = gpd.GeoDataFrame(geometry=hazard_zones_buffered, crs="EPSG:4326")
    schools_around_hazard = gpd.sjoin(schools_gdf, hazard_zones_buffered_gdf, how="inner").drop(schools_in_hazard.index, errors='ignore')

    # Map hazard zones, schools in zones, and nearby schools
    folium.GeoJson(hazard_zones, name="Hazard Zones", style_function=lambda x: {
        "fillColor": "red", "color": "red", "fillOpacity": 0.5
    }).add_to(m)
    
    # Hazard zone schools (Red)
    for _, row in schools_in_hazard.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"{row['name']} (In Hazard Zone)",
            icon=folium.Icon(color="red", icon="warning")
        ).add_to(m)

    # Nearby schools (Orange)
    for _, row in schools_around_hazard.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"{row['name']} (Near Hazard Zone)",
            icon=folium.Icon(color="orange", icon="info-sign")
        ).add_to(m)

    folium.GeoJson(tamil_nadu_map, name="Tamil Nadu").add_to(m)
    st_folium(m, width=700, height=500)
    
# Weather and Cyclone Status using Windy
elif analysis_type == "Weather & Cyclone Status":
    st.subheader("Current Weather and Cyclone Status")
    st.markdown("This feature displays live cyclone and weather data from Windy.")

    # Embed Windy map
    windy_url = "https://embed.windy.com/embed2.html?lat=12.98&lon=80.18&zoom=6&level=surface&overlay=wind&menu=&message=true&marker=true&calendar=now&pressure=true&type=map&location=coordinates&detail=true&detailLat=12.98&detailLon=80.18&metricWind=default&metricTemp=default&radarRange=-1"
    
    # IFrame for embedding
    st.components.v1.html(
        f'<iframe width="1200" height="700" src="{windy_url}" frameborder="0"></iframe>',
        height=900, width=1500,
    )