import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import rasterio
import numpy as np
from branca.element import Template, MacroElement

st.set_page_config(page_title="Dashboard LULC", layout="wide")

# ==========================================
# KONFIGURASI KELAS (satu sumber untuk warna, filter, dan legenda)
# ==========================================
# (id piksel, nama, warna RGB)
KELAS = [
    (1, "Perairan",       (44, 123, 182)),
    (2, "Hutan Biasa",    (0, 128, 0)),
    (3, "Hutan Mangrove", (0, 204, 102)),
    (4, "Sawah",          (255, 255, 0)),
    (5, "Bangunan",       (215, 25, 28)),
]

FILE_TIF = "Hasil_Klasifikasi_LULC.tif"
FILE_GEOJSON = "UTS_data.geojson"

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
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }

    section[data-testid="stSidebar"] {
        background-color: #E9EEF0;
        border-right: 1px solid #CBD5D9;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-weight: 600;
        color: #1D2B33 !important;
    }
    
    /* Memaksa teks di sidebar menjadi gelap agar terlihat di background terang */
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
# STATE
# ==========================================
for _id, nama, _ in KELAS:
    st.session_state.setdefault(f"kelas_{_id}", True)   # default: semua tampil
st.session_state.setdefault("view", {"center": [-7.6, 112.5], "zoom": 8})


def set_semua(nilai: bool):
    for _id, _, _ in KELAS:
        st.session_state[f"kelas_{_id}"] = nilai


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.subheader("Tampilan peta")

    # Slider skala 0 - 100 persen
    opacity_level = st.slider(
        "Transparansi hasil klasifikasi",
        min_value=0,
        max_value=100,
        value=60,
        step=5,
        format="%d%%",
        help="Geser ke kiri (0%) untuk melihat citra satelit murni, ke kanan (100%) untuk tebakan model pekat.",
    )

    st.divider()
    st.subheader("Kelas tutupan lahan")

    kol_a, kol_b = st.columns(2)
    kol_a.button("Pilih semua", on_click=set_semua, args=(True,), use_container_width=True)
    kol_b.button("Kosongkan", on_click=set_semua, args=(False,), use_container_width=True)

    # Checkbox per kelas -> logika OR (1, beberapa, atau semua kelas)
    for id_kelas, nama, _ in KELAS:
        st.checkbox(nama, key=f"kelas_{id_kelas}")

id_kelas_aktif = [i for i, _, _ in KELAS if st.session_state[f"kelas_{i}"]]

# ==========================================
# DATA (di-cache supaya tidak dibaca ulang tiap interaksi)
# ==========================================
@st.cache_data(show_spinner="Membaca raster...")
def muat_raster(path):
    with rasterio.open(path) as src:
        data = src.read(1)
        b = src.bounds
        crs = src.crs.to_string() if src.crs else None
    return data, (b.bottom, b.left, b.top, b.right), crs


@st.cache_data(show_spinner="Membaca poligon...")
def muat_poligon(path):
    return gpd.read_file(path)


def buat_rgba(data, aktif, opacity_persen):
    """Warna kelas dan alpha digabung langsung di piksel,
    jadi slider transparansi pasti terlihat pada warna kelas."""
    # Konversi dari persentase (0-100) ke skala desimal (0-1) lalu ke alpha 8-bit (0-255)
    alpha = int(round((opacity_persen / 100.0) * 255))
    
    lut = np.zeros((256, 4), dtype=np.uint8)   # indeks 0 = transparan
    for id_kelas, _, (r, g, b) in KELAS:
        if id_kelas in aktif:
            lut[id_kelas] = [r, g, b, alpha]

    idx = np.where(np.isin(data, [k[0] for k in KELAS]), data, 0).astype(np.uint8)
    return lut[idx]


# ==========================================
# HALAMAN UTAMA
# ==========================================
st.markdown('<p class="judul-halaman">Klasifikasi Tutupan Lahan (LULC)</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-halaman">Hasil klasifikasi model dibandingkan dengan poligon data asli.</p>',
    unsafe_allow_html=True,
)

view = st.session_state["view"]
m = folium.Map(location=view["center"], zoom_start=view["zoom"])

# 1. LAYER BASEMAP
folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attr="Google",
    name="Layer 1: Google Hybrid (Satelit & Label)",
    overlay=False,
    control=True,
).add_to(m)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google",
    name="Layer 1: Google Satellite (Polos)",
    overlay=False,
    control=True,
).add_to(m)

# 2. LAYER TIF (HASIL KLASIFIKASI MODEL)
try:
    data, (bawah, kiri, atas, kanan), crs = muat_raster(FILE_TIF)

    if crs and crs.upper() != "EPSG:4326":
        st.warning(
            f"Raster memakai {crs}, bukan EPSG:4326. Posisi overlay bisa meleset; "
            "reproyeksi dulu ke EPSG:4326."
        )

    rgba = buat_rgba(data, id_kelas_aktif, opacity_level)

    folium.raster_layers.ImageOverlay(
        image=rgba,
        bounds=[[bawah, kiri], [atas, kanan]],
        name="Layer 2: Hasil Klasifikasi Model",
        opacity=1.0,   # transparansi sudah ada di kanal alpha piksel dari buat_rgba
        show=True,
    ).add_to(m)
except Exception as e:
    st.error(f"Gagal memuat raster: {e}")

# 3. LAYER POLYGON (DATA ASLI)
try:
    gdf = muat_poligon(FILE_GEOJSON)

    tooltip_poligon = folium.GeoJsonTooltip(
        fields=["Class"],
        aliases=["Data asli (poligon): "],
        style=(
            "background-color: white; color: black; font-weight: bold; padding: 10px; "
            "border: 2px solid #333; border-radius: 5px; font-size: 13px;"
        ),
    )

    folium.GeoJson(
        gdf,
        name="Layer 3: Poligon Data Asli",
        style_function=lambda x: {"color": "#FFFF00", "weight": 2.5, "fillOpacity": 0.1},
        tooltip=tooltip_poligon,
    ).add_to(m)
except Exception as e:
    st.error(f"Gagal memproses poligon: {e}")

# ==========================================
# LEGENDA (hanya menampilkan kelas yang aktif)
# ==========================================
baris = ""
for id_kelas, nama, (r, g, b) in KELAS:
    if id_kelas in id_kelas_aktif:
        baris += (
            '<div style="display:flex; align-items:center; margin-bottom:7px;">'
            f'<span style="background:rgb({r},{g},{b}); width:14px; height:14px; '
            'border-radius:2px; margin-right:10px; border:1px solid rgba(0,0,0,0.25);"></span>'
            f"{nama}</div>"
        )
if not baris:
    baris = '<div style="color:#666;">Tidak ada kelas dipilih</div>'

legenda_html = (
    "{% macro html(this, kwargs) %}"
    '<div style="position:absolute; bottom:30px; left:30px; min-width:180px; '
    "background-color:white !important; color:#1D2B33 !important; z-index:9999; "
    "font-size:13px; font-family:Arial, sans-serif; border:1px solid #B8C4C9; "
    'border-radius:4px; padding:12px 14px; box-shadow:0 1px 4px rgba(0,0,0,0.25);">'
    '<div style="font-size:14px; font-weight:bold; margin-bottom:10px;">Legenda LULC</div>'
    + baris
    + "</div>{% endmacro %}"
)
macro = MacroElement()
macro._template = Template(legenda_html)
m.get_root().add_child(macro)

folium.LayerControl(collapsed=False).add_to(m)

# ==========================================
# RENDER PETA DENGAN KUNCI STATIS (Mencegah Tumpukan Redup)
# ==========================================
hasil = st_folium(
    m,
    use_container_width=True,
    height=700,
    key="peta_utama_lulc", # Kunci dibuat statis agar tidak dirender ulang secara bertumpuk
    returned_objects=["center", "zoom"],
)

# Simpan posisi & zoom terakhir agar peta tidak lompat saat filter diubah
if hasil and hasil.get("center") and hasil.get("zoom"):
    st.session_state["view"] = {
        "center": [hasil["center"]["lat"], hasil["center"]["lng"]],
        "zoom": hasil["zoom"],
    }