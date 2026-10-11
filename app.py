import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import joblib
import pandas as pd

st.set_page_config(
    page_title="Peta LULC Jawa Timur", 
    layout="wide"
)

# Header Aplikasi
st.title("Web GIS Klasifikasi Tutupan Lahan (LULC) Provinsi Jawa Timur")
st.markdown("Aplikasi interaktif analisis spasial tutupan lahan berbasis piksel menggunakan algoritma **Random Forest**.")

# Memuat Model Klasifikasi
@st.cache_resource
def load_model():
    return joblib.load('model_rf.pkl')

model = load_model()

# Sidebar Kontrol Layer
st.sidebar.header("Kontrol Lapisan Peta")
tampil_poligon = st.sidebar.checkbox("Tampilkan Poligon Sampel Ground Truth", value=True)
tampil_basemap = st.sidebar.selectbox(
    "Pilih Peta Dasar (Basemap)", 
    ["OpenStreetMap", "Satelit Esri (Imagery)"]
)

# Inisialisasi Lokasi Tengah Peta (Jawa Timur)
lat_jatim, lon_jatim = -7.53606, 112.2384

if tampil_basemap == "Satelit Esri (Imagery)":
    m = folium.Map(
        location=[lat_jatim, lon_jatim], 
        zoom_start=9, 
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )
else:
    m = folium.Map(location=[lat_jatim, lon_jatim], zoom_start=9, tiles='OpenStreetMap')

# Penambahan Layer Vektor Geometris GeoJSON
try:
    gdf = gpd.read_file("UTS_data.geojson") 
    if tampil_poligon:
        folium.GeoJson(
            gdf,
            name="Poligon Sampel",
            style_function=lambda x: {'color': '#e74c3c', 'fillColor': '#e67e22', 'fillOpacity': 0.3}
        ).add_to(m)
except Exception as e:
    st.sidebar.info("Sistem memuat peta tanpa overlay vektor (UTS_data.geojson tidak ditemukan).")

folium.LayerControl().add_to(m)

# Visualisasi Peta Spasial
st.subheader("Visualisasi Sebaran Spasial Interaktif")
st_folium(m, width=1200, height=550)

# Legenda Klasifikasi Tutupan Lahan
st.markdown("### Legenda Kelas Lahan")
col1, col2, col3, col4, col5 = st.columns(5)
col1.info("Perairan")
col2.success("Hutan Lebat")
col3.warning("Hutan Mangrove")
col4.error("Sawah / Pertanian")
col5.markdown("<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #d1d5db; font-weight: bold;'>Bangunan / Permukiman</div>", unsafe_allow_code=True)
