import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import rasterio
import numpy as np
from branca.element import Template, MacroElement

st.set_page_config(page_title="Dashboard LULC Spasial", layout="wide")

st.title("Web GIS Klasifikasi Tutupan Lahan (LULC)")
st.markdown("Visualisasi spasial hasil pemetaan berbasis piksel menggunakan model Machine Learning Random Forest.")

# Inisialisasi peta dasar dengan koordinat wilayah kajian
m = folium.Map(location=[-7.25, 112.70], zoom_start=11)

# Penambahan lapisan basemap Google Satellite
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Satellite',
    overlay=False,
    control=True
).add_to(m)

# Pemrosesan dan pewarnaan data raster TIF
try:
    with rasterio.open('Hasil_Klasifikasi_LULC.tif') as src:
        data = src.read(1)
        bounds = src.bounds
        
    # Inisialisasi kanvas matriks RGBA kosong untuk pewarnaan spasial
    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
    
    # Pemetaan nilai integer biner raster ke kode warna RGB [Red, Green, Blue, Alpha]
    rgba[data == 1] = [44, 123, 182, 255]   # Perairan (Biru)
    rgba[data == 2] = [0, 128, 0, 255]      # Hutan (Hijau Tua)
    rgba[data == 3] = [0, 204, 102, 255]    # Hutan Mangrove (Hijau Terang)
    rgba[data == 4] = [255, 255, 0, 255]    # Sawah (Kuning)
    rgba[data == 5] = [215, 25, 28, 255]    # Bangunan (Merah)
    rgba[data == 0] = [0, 0, 0, 0]          # NoData / Background (Transparan)

    # Overlay lapisan citra hasil klasifikasi ke atas peta folium
    folium.raster_layers.ImageOverlay(
        image=rgba,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        opacity=0.7, 
        name='Hasil Klasifikasi Random Forest'
    ).add_to(m)
    
except Exception as e:
    st.error(f"Gagal memuat file raster TIF: {e}")

# Pemuatan lapisan vektor poligon acuan GeoJSON
try:
    gdf = gpd.read_file("UTS_data.geojson") 
    folium.GeoJson(
        gdf,
        name="Poligon Acuan (Ground Truth)",
        style_function=lambda x: {'color': '#ffffff', 'weight': 1.5, 'fillOpacity': 0.3}
    ).add_to(m)
except Exception:
    pass

# Komponen HTML legenda interaktif
legenda_html = """
{% macro html(this, kwargs) %}
<div style="position: absolute; bottom: 30px; left: 30px; width: 260px; background-color: white; z-index:9999; font-size:13px; border: 1px solid #d1d5db; border-radius: 6px; padding: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <h4 style="margin-top:0; margin-bottom:12px; font-size:14px; font-family: sans-serif; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px;"><b>Legenda LULC</b></h4>
    <div style="margin-bottom: 8px;"><i style="background:rgb(44,123,182); width: 16px; height: 16px; float: left; margin-right: 10px; border-radius: 2px;"></i> Perairan</div>
    <div style="margin-bottom: 8px;"><i style="background:rgb(0,128,0); width: 16px; height: 16px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan</div>
    <div style="margin-bottom: 8px;"><i style="background:rgb(0,204,102); width: 16px; height: 16px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan Mangrove</div>
    <div style="margin-bottom: 8px;"><i style="background:rgb(255,255,0); width: 16px; height: 16px; float: left; margin-right: 10px; border-radius: 2px;"></i> Sawah</div>
    <div style="margin-bottom: 4px;"><i style="background:rgb(215,25,28); width: 16px; height: 16px; float: left; margin-right: 10px; border-radius: 2px;"></i> Bangunan</div>
</div>
{% endmacro %}
"""
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

# Mengaktifkan panel kontrol visibilitas layer
folium.LayerControl(collapsed=False).add_to(m)

# Integrasi visualisasi peta ke panel utama Streamlit
st_folium(m, use_container_width=True, height=700)
