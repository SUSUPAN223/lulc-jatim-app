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
# 1. LAYER PALING BAWAH (MAP ASLI)
# ==========================================
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Hybrid (Satelit Asli)',
    overlay=False,
    control=True
).add_to(m)

# ==========================================
# 2. LAYER TIF (PILIHAN MAU AKTIFIN TIF/ENGGA)
# ==========================================
try:
    with rasterio.open('Hasil_Klasifikasi_LULC.tif') as src:
        data = src.read(1)
        bounds = src.bounds
        
    # Satu kanvas transparan 50% untuk seluruh prediksi
    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
    rgba[data == 1] = [44, 123, 182, 255]   # Air
    rgba[data == 2] = [0, 128, 0, 255]      # Hutan
    rgba[data == 3] = [0, 204, 102, 255]    # Mangrove
    rgba[data == 4] = [255, 255, 0, 255]    # Sawah
    rgba[data == 5] = [215, 25, 28, 255]    # Bangunan
    
    folium.raster_layers.ImageOverlay(
        image=rgba,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        name="Layer 2: Tebakan Model TIF",
        opacity=0.5,
        show=True  # Bisa di-uncentang di pojok kanan atas
    ).add_to(m)
except Exception as e:
    st.error(f"Gagal memuat raster: {e}")

# ==========================================
# 3 & 4. LAYER POLYGON & NOTIFIKASI VALIDASI
# ==========================================
try:
    gdf = gpd.read_file("UTS_data.geojson") 
    
    # Proses membaca TIF untuk mengecek tebakan pada tiap poligon
    with rasterio.open('Hasil_Klasifikasi_LULC.tif') as src:
        # Ambil titik tengah dari tiap poligon
        centroids = gdf.geometry.centroid
        koordinat = [(geom.x, geom.y) for geom in centroids]
        
        # Baca nilai TIF tepat di koordinat poligon tersebut
        nilai_prediksi = [val[0] for val in src.sample(koordinat)]
        
        # Terjemahkan angka kembali ke nama kelas
        kamus_balik = {
            1: 'Perairan', 2: 'Hutan', 3: 'Hutan Mangrove', 
            4: 'Sawah', 5: 'Bangunan', 0: 'Tidak Terdeteksi'
        }
        
        # Simpan tebakan ke dalam data poligon (Layer 4)
        gdf['Tebakan_Model'] = [kamus_balik.get(val, 'Tidak Terdeteksi') for val in nilai_prediksi]
    
    # Tampilkan label notifikasi (Layer 3 & 4 digabung dalam tooltip)
    tooltip_poligon = folium.GeoJsonTooltip(
        fields=['Class', 'Tebakan_Model'], 
        aliases=['🎯 Data Asli (Polygon) :', '🤖 Tebakan Model (TIF) :'],
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
# LEGENDA (Tetap putih agar tidak tertimpa Dark Mode)
# ==========================================
legenda_html = """
{% macro html(this, kwargs) %}
<div style="position: absolute; bottom: 30px; left: 30px; width: 220px; 
    background-color: white !important; color: #333 !important; z-index:9999; 
    font-size:13px; font-family: Arial, sans-serif; border: 1px solid #ccc; 
    border-radius: 8px; padding: 15px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h4 style="margin-top:0; margin-bottom:10px; font-size:15px; color: black !important;"><b>Legenda LULC</b></h4>
    <i style="background:rgb(44,123,182); width: 15px; height: 15px; float: left; margin-right: 10px;"></i> Perairan<br><br>
    <i style="background:rgb(0,204,102); width: 15px; height: 15px; float: left; margin-right: 10px;"></i> Hutan Mangrove<br><br>
    <i style="background:rgb(0,128,0); width: 15px; height: 15px; float: left; margin-right: 10px;"></i> Hutan Biasa<br><br>
    <i style="background:rgb(215,25,28); width: 15px; height: 15px; float: left; margin-right: 10px;"></i> Bangunan<br><br>
    <i style="background:rgb(255,255,0); width: 15px; height: 15px; float: left; margin-right: 10px;"></i> Sawah<br>
</div>
{% endmacro %}
"""
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

# Menampilkan kontrol layer (bisa centang/uncentang)
folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, use_container_width=True, height=700)
