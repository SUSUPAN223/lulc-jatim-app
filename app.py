import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
import numpy as np
from branca.element import Template, MacroElement

st.set_page_config(page_title="Dashboard LULC Jawa Timur", layout="wide")

# ==========================================
# KONFIGURASI KELAS & FILE
# ==========================================
KELAS = [
    (1, "Perairan",       (44, 123, 182)),
    (2, "Hutan Biasa",    (0, 128, 0)),
    (3, "Hutan Mangrove", (0, 204, 102)),
    (4, "Sawah",          (255, 255, 0)),
    (5, "Bangunan",       (215, 25, 28)),
]

FILE_TIF = "Hasil_Klasifikasi_LULC_Kecil.tif"
FILE_GEOJSON = "Update22.geojson"

# ==========================================
# TAMPILAN (CSS)
# ==========================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stMarkdown, label, button {
        font-family: 'Instrument Sans', sans-serif;
    }
    .block-container { padding-top: 1.8rem; padding-bottom: 1rem; }

    div[data-stale="true"] {
        opacity: 1 !important;
        transition: none !important;
    }
    iframe {
        opacity: 1 !important;
        filter: none !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #E9EEF0;
        border-right: 1px solid #CBD5D9;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-weight: 600;
        color: #1D2B33 !important;
    }
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stWidgetLabel p {
        color: #1D2B33 !important;
    }

    .judul-halaman {
        font-size: 1.75rem;
        font-weight: 600;
        color: #1D2B33;
        line-height: 1.2;
        margin: 0 0 0.25rem 0;
    }
    .sub-halaman {
        color: #55656D;
        font-size: 0.95rem;
        margin: 0 0 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# INISIALISASI STATE
# ==========================================
for _id, _, _ in KELAS:
    if f"cb_kelas_{_id}" not in st.session_state:
        st.session_state[f"cb_kelas_{_id}"] = True


def pilih_semua_kelas():
    for _id, _, _ in KELAS:
        st.session_state[f"cb_kelas_{_id}"] = True


def kosongkan_semua_kelas():
    for _id, _, _ in KELAS:
        st.session_state[f"cb_kelas_{_id}"] = False


# ==========================================
# SIDEBAR FILTER & KONTROL
# ==========================================
with st.sidebar:
    st.subheader("Mode Tampilan Peta")

    pilihan_mode = [
        "Gabungan (Peta + TIF)",
        "Hanya Peta Dasar (Map Saja)",
        "Hanya Hasil Klasifikasi (TIF Saja)",
        "Fokus 1 Kelas Tertentu",
    ]
    mode_tampilan = st.radio(
        "Pilih Mode Visualisasi:",
        options=pilihan_mode,
        index=0,
    )

    pilihan_basemap = st.selectbox(
        "Pilih Peta Dasar (Basemap):",
        options=[
            "Google Streets (Terang & Jelas)",
            "CartoDB Positron (Putih Bersih)",
            "Google Hybrid (Satelit + Nama Jalan)",
            "Google Satellite (Satelit Polos)",
        ],
        index=0,
    )

    tampilkan_poligon = st.checkbox("Tampilkan Poligon Sampel Asli", value=False)

    st.divider()
    st.subheader("Pengaturan Transparansi")

    opacity_level = st.slider(
        "Transparansi Klasifikasi (TIF)",
        min_value=0,
        max_value=100,
        value=75,
        step=5,
        format="%d%%",
        disabled=(mode_tampilan == "Hanya Peta Dasar (Map Saja)"),
        help="0% = Transparan penuh (tidak terlihat), 100% = Warna solid pekat.",
    )

    st.divider()
    st.subheader("Filter Kelas Tutupan Lahan")

    id_kelas_aktif = []

    if mode_tampilan == "Hanya Peta Dasar (Map Saja)":
        st.info("Mode 'Hanya Peta Dasar' aktif. Layer klasifikasi TIF disembunyikan.")
        id_kelas_aktif = []

    elif mode_tampilan == "Fokus 1 Kelas Tertentu":
        nama_ke_id = {nama: _id for _id, nama, _ in KELAS}
        kelas_terpilih = st.selectbox(
            "Pilih 1 Kelas untuk Ditampilkan:",
            options=list(nama_ke_id.keys()),
        )
        id_kelas_aktif = [nama_ke_id[kelas_terpilih]]

    else:
        kol_a, kol_b = st.columns(2)
        if kol_a.button("Pilih Semua", use_container_width=True):
            pilih_semua_kelas()
            st.rerun()
        if kol_b.button("Kosongkan", use_container_width=True):
            kosongkan_semua_kelas()
            st.rerun()

        for id_kelas, nama, _ in KELAS:
            centang = st.checkbox(nama, key=f"cb_kelas_{id_kelas}")
            if centang:
                id_kelas_aktif.append(id_kelas)


# ==========================================
# FUNGSI PEMUATAN DATA (OPTIMASI MEMORI)
# ==========================================
@st.cache_data(show_spinner="Memuat citra klasifikasi Jawa Timur...")
def muat_raster(path, max_dim=2400):
    with rasterio.open(path) as src:
        skala = min(1.0, max_dim / max(src.height, src.width))
        tinggi_baru = max(1, int(src.height * skala))
        lebar_baru = max(1, int(src.width * skala))

        data = src.read(
            1,
            out_shape=(tinggi_baru, lebar_baru),
            resampling=Resampling.nearest,
        )
        b = src.bounds
        crs = src.crs.to_string() if src.crs else None
    return data, (b.bottom, b.left, b.top, b.right), crs


@st.cache_data(show_spinner="Memuat poligon sampel...")
def muat_poligon(path):
    gdf = gpd.read_file(path)
    if "Class" in gdf.columns:
        gdf["Class_Clean"] = gdf["Class"].astype(str).str.strip()
        gdf = gdf[gdf["Class_Clean"] != "JAWA TIMUR"].copy()
    return gdf


def buat_rgba(data, aktif, opacity_persen):
    alpha = int(round((opacity_persen / 100.0) * 255))
    lut = np.zeros((256, 4), dtype=np.uint8)
    for id_kelas, _, (r, g, b) in KELAS:
        if id_kelas in aktif:
            lut[id_kelas] = [r, g, b, alpha]

    idx = np.where(np.isin(data, [k[0] for k in KELAS]), data, 0).astype(np.uint8)
    return lut[idx]


# ==========================================
# RENDER HALAMAN UTAMA & PETA
# ==========================================
st.markdown('<p class="judul-halaman">Dashboard Klasifikasi Tutupan Lahan (LULC) Jawa Timur</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-halaman">Visualisasi interaktif pemetaan tutupan lahan Provinsi Jawa Timur berbasis Sentinel-2 & Random Forest.</p>',
    unsafe_allow_html=True,
)

m = folium.Map(
    location=[-7.75, 112.75],
    zoom_start=8,
    tiles=None,
    control_scale=True,
)

if mode_tampilan == "Hanya Hasil Klasifikasi (TIF Saja)":
    folium.TileLayer(
        tiles="",
        attr="Kanvas Kosong",
        name="Kanvas Polos (Tanpa Peta)",
        overlay=False,
        control=False,
    ).add_to(m)
else:
    kamus_tiles = {
        "Google Streets (Terang & Jelas)": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "CartoDB Positron (Putih Bersih)": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "Google Hybrid (Satelit + Nama Jalan)": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "Google Satellite (Satelit Polos)": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    }
    folium.TileLayer(
        tiles=kamus_tiles[pilihan_basemap],
        attr="Basemap",
        name=pilihan_basemap,
        overlay=False,
        control=False,
    ).add_to(m)

if mode_tampilan != "Hanya Peta Dasar (Map Saja)" and len(id_kelas_aktif) > 0 and opacity_level > 0:
    try:
        data, (bawah, kiri, atas, kanan), crs = muat_raster(FILE_TIF)
        rgba = buat_rgba(data, id_kelas_aktif, opacity_level)

        folium.raster_layers.ImageOverlay(
            image=rgba,
            bounds=[[bawah, kiri], [atas, kanan]],
            name="Hasil Klasifikasi LULC",
            opacity=1.0,
            interactive=False,
            cross_origin=False,
            zindex=2,
        ).add_to(m)
    except Exception as e:
        st.error(f"Gagal memuat file raster '{FILE_TIF}': {e}")

if tampilkan_poligon:
    try:
        gdf = muat_poligon(FILE_GEOJSON)
        tooltip_poligon = folium.GeoJsonTooltip(
            fields=["Class_Clean"],
            aliases=["Kelas Sampel Asli: "],
            style=(
                "background-color: white; color: black; font-weight: bold; padding: 8px; "
                "border: 1px solid #333; border-radius: 4px; font-size: 12px;"
            ),
        )
        folium.GeoJson(
            gdf,
            name="Poligon Sampel Asli",
            style_function=lambda x: {
                "color": "#FF6600",
                "weight": 2,
                "fillColor": "#FFFF00",
                "fillOpacity": 0.25,
            },
            tooltip=tooltip_poligon,
        ).add_to(m)
    except Exception as e:
        st.error(f"Gagal memproses poligon '{FILE_GEOJSON}': {e}")

# ==========================================
# LEGENDA DINAMIS
# ==========================================
baris_legenda = ""
for id_kelas, nama, (r, g, b) in KELAS:
    if id_kelas in id_kelas_aktif:
        baris_legenda += (
            '<div style="display:flex; align-items:center; margin-bottom:7px;">'
            f'<span style="background:rgb({r},{g},{b}); width:14px; height:14px; '
            'border-radius:2px; margin-right:10px; border:1px solid rgba(0,0,0,0.25);"></span>'
            f"{nama}</div>"
        )
if not baris_legenda:
    baris_legenda = '<div style="color:#666;">Layer TIF disembunyikan</div>'

legenda_html = (
    "{% macro html(this, kwargs) %}"
    '<div style="position:fixed; bottom:35px; left:35px; min-width:185px; '
    "background-color:white !important; color:#1D2B33 !important; z-index:9999; "
    "font-size:13px; font-family:Arial, sans-serif; border:1px solid #B8C4C9; "
    'border-radius:6px; padding:12px 14px; box-shadow:0 2px 6px rgba(0,0,0,0.2);">'
    '<div style="font-size:14px; font-weight:bold; margin-bottom:10px;">Legenda LULC</div>'
    + baris_legenda
    + "</div>{% endmacro %}"
)
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

st_folium(
    m,
    use_container_width=True,
    height=680,
    key="peta_lulc_jatim",
    returned_objects=[],
)