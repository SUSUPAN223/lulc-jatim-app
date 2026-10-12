import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import rasterio
import numpy as np
from branca.element import Template, MacroElement

st.set_page_config(page_title="Dashboard LULC", layout="wide")
st.title("🗺️ Web GIS Klasifikasi Tutupan Lahan (LULC)")

m = folium.Map(location=[-7.6, 112.5], zoom_start=8)

# ==========================================
# 1. LAYER BASEMAP
# ==========================================
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Layer 1: Google Hybrid (Satelit & Label)',
    overlay=False,
    control=True
).add_to(m)

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google',
    name='Layer 1: Google Satellite (Polos)',
    overlay=False,
    control=True
).add_to(m)

# ==========================================
# 2. LAYER TIF (TEBAKAN MODEL)
# ==========================================
try:
    with rasterio.open('Hasil_Klasifikasi_LULC.tif') as src:
        data = src.read(1)
        bounds = src.bounds
        
    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
    rgba[data == 1] = [44, 123, 182, 255]   # Air
    rgba[data == 2] = [0, 128, 0, 255]      # Hutan Biasa
    rgba[data == 3] = [0, 204, 102, 255]    # Hutan Mangrove
    rgba[data == 4] = [255, 255, 0, 255]    # Sawah
    rgba[data == 5] = [215, 25, 28, 255]    # Bangunan
    
    folium.raster_layers.ImageOverlay(
        image=rgba,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        name="Layer 2: Tebakan Model TIF",
        opacity=0.5,
        show=True
    ).add_to(m)
except Exception as e:
    st.error(f"Gagal memuat raster: {e}")

# ==========================================
# 3. LAYER POLYGON (DATA ASLI)
# ==========================================
try:
    gdf = gpd.read_file("UTS_data.geojson") 
    
    # Tooltip HANYA memuat kelas aslinya saja agar konsisten dan tidak menyesatkan
    tooltip_poligon = folium.GeoJsonTooltip(
        fields=['Class'], 
        aliases=['🎯 Data Asli (Polygon) : '],
        style="background-color: white; color: black; font-weight: bold; padding: 10px; border: 2px solid #333; border-radius: 5px; font-size: 13px;"
    )
    
    folium.GeoJson(
        gdf,
        name="Layer 3: Poligon Data Asli",
        style_function=lambda x: {'color': '#FFFF00', 'weight': 2.5, 'fillOpacity': 0.1},
        tooltip=tooltip_poligon
    ).add_to(m)
except Exception as e:
    st.error(f"Gagal memproses poligon: {e}")

# ==========================================
# LEGENDA
# ==========================================
legenda_html = """
{% macro html(this, kwargs) %}
<div style="position: absolute; bottom: 30px; left: 30px; width: 220px; 
    background-color: white !important; color: #333 !important; z-index:9999; 
    font-size:13px; font-family: Arial, sans-serif; border: 1px solid #ccc; 
    border-radius: 8px; padding: 15px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h4 style="margin-top:0; margin-bottom:10px; font-size:15px; color: black !important;"><b>Legenda LULC</b></h4>
    <i style="background:rgb(44,123,182); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Perairan<br><br>
    <i style="background:rgb(0,204,102); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan Mangrove<br><br>
    <i style="background:rgb(0,128,0); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan Biasa<br><br>
    <i style="background:rgb(215,25,28); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Bangunan<br><br>
    <i style="background:rgb(255,255,0); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Sawah<br>
</div>
{% endmacro %}
"""
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

# Mengaktifkan panel layer control di kanan atas
folium.LayerControl(collapsed=False).add_to(m)

# Render map di Streamlit
st_folium(m, use_container_width=True, height=700)
