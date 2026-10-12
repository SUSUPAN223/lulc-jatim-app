import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import rasterio
import numpy as np
from branca.element import Template, MacroElement

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Dashboard LULC", layout="wide")
st.title("🗺️ Web GIS Klasifikasi Tutupan Lahan (LULC)")
st.markdown("Visualisasi spasial berbasis model Machine Learning Random Forest.")

# 1. BASEMAP GOOGLE (Satelit & Hybrid)
# Titik tengah peta difokuskan ke Jawa Timur
m = folium.Map(location=[-7.6, 112.5], zoom_start=8)

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Hybrid (Label)',
    overlay=False,
    control=True
).add_to(m)

folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Satellite',
    overlay=False,
    control=True
).add_to(m)

# 2. MEMUAT RASTER (DENGAN EFEK TEMBUS PANDANG)
try:
    with rasterio.open('Hasil_Klasifikasi_LULC.tif') as src:
        data = src.read(1)
        bounds = src.bounds
        
    valid_pixels = np.sum(data > 0)
    
    # Kamus Kelas: [Nilai, Nama Kelas, Warna RGB]
    kelas_lulc = {
        1: ('LULC: Air', [44, 123, 182, 255]),
        4: ('LULC: Sawah', [255, 255, 0, 255]),
        5: ('LULC: Pemukiman', [215, 25, 28, 255]),
        2: ('LULC: Hutan Non-Mangrove', [0, 128, 0, 255]),
        3: ('LULC: Hutan Mangrove', [0, 204, 102, 255])
    }

    persentase_teks = {}

    # Membangun layer per kelas secara terpisah
    for val, (nama, warna) in kelas_lulc.items():
        pct = (np.sum(data == val) / valid_pixels) * 100 if valid_pixels > 0 else 0
        nama_layer = f"{nama} ({pct:.2f}%)"
        persentase_teks[val] = f"{pct:.2f}%"
        
        # Kanvas transparan khusus kelas ini
        rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)
        rgba[data == val] = warna
        
        folium.raster_layers.ImageOverlay(
            image=rgba,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            name=nama_layer,
            opacity=0.45,  # Efek kaca agar satelit di bawahnya terlihat
            show=True
        ).add_to(m)
        
except Exception as e:
    st.error(f"Gagal memuat raster: {e}")

# 3. MEMUAT POLIGON DENGAN TOOLTIP (Label Interaktif)
try:
    gdf = gpd.read_file("UTS_data.geojson") 
    
    # Tooltip muncul saat kursor menyentuh poligon
    tooltip_poligon = folium.GeoJsonTooltip(
        fields=['Class'], 
        aliases=['🎯 Kelas Asli (Ground Truth) : '],
        style="background-color: white; color: black; font-weight: bold; padding: 8px; border: 2px solid #333; border-radius: 5px; box-shadow: 2px 2px 4px rgba(0,0,0,0.3);"
    )
    
    folium.GeoJson(
        gdf,
        name="Poligon Sampel Acuan",
        style_function=lambda x: {'color': '#FFFF00', 'weight': 2.5, 'fillOpacity': 0.1}, # Kuning menyala agar terlihat jelas di satelit
        tooltip=tooltip_poligon
    ).add_to(m)
except Exception:
    pass

# 4. LEGENDA KEBUN ANTI DARK-MODE
legenda_html = f"""
{{% macro html(this, kwargs) %}}
<div style="position: absolute; bottom: 30px; left: 30px; width: 280px; 
    background-color: white !important; color: #333 !important; z-index:9999; 
    font-size:13px; font-family: Arial, sans-serif; border: 1px solid #ccc; 
    border-radius: 8px; padding: 15px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h4 style="margin-top:0; margin-bottom:10px; font-size:15px; color: black !important;"><b>Legenda LULC Jawa Timur</b></h4>
    
    <i style="background:rgb(44,123,182); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Air ({persentase_teks.get(1, '0%')})<br><br>
    <i style="background:rgb(0,204,102); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan Mangrove ({persentase_teks.get(3, '0%')})<br><br>
    <i style="background:rgb(0,128,0); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Hutan Non-Mangrove ({persentase_teks.get(2, '0%')})<br><br>
    <i style="background:rgb(215,25,28); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Pemukiman ({persentase_teks.get(5, '0%')})<br><br>
    <i style="background:rgb(255,255,0); width: 15px; height: 15px; float: left; margin-right: 10px; border-radius: 2px;"></i> Sawah ({persentase_teks.get(4, '0%')})<br>
    
    <hr style="margin: 10px 0; border-top: 1px solid #ddd;">
    <span style="font-size: 11px; color: #666 !important;">Model: Random Forest | Resolusi: 100m</span>
</div>
{{% endmacro %}}
"""
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

# 5. KUNCI LAYER CONTROL
folium.LayerControl(collapsed=False).add_to(m)

# Render Peta
st_folium(m, use_container_width=True, height=700)
