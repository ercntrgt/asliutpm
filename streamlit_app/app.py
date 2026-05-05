"""UTPM Karar Destek Asistanı — Streamlit prototipi.

Çalıştırma:
    cd streamlit_app
    streamlit run app.py

Anthropic API key opsiyonel. ``.streamlit/secrets.toml`` veya
``$env:ANTHROPIC_API_KEY`` ortam değişkeni ile sağlanır. Yoksa
template-based yorum kullanılır.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

# Proje kök dizinini sys.path'e ekle
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.utils import (  # noqa: E402
    load_all_data, find_cell_by_coords, cell_summary, neighborhood_comparison,
    JENKS_LABELS, LISA_DESCRIPTIONS,
)
from streamlit_app.claude_explainer import explain_with_claude  # noqa: E402


# ============================================================================
# Sayfa konfigürasyonu
# ============================================================================
st.set_page_config(
    page_title="UTPM Konyaaltı — Karar Destek",
    page_icon="🌡️",
    layout="wide",
)

st.title("🌡️ UTPM Konyaaltı — Karar Destek Asistanı")
st.caption(
    "Urban Thermal Persistence Model — kentsel ısı kalıcılık tarama aracı. "
    "Haritada bir konuma tıklayın → o noktanın UTPM skoru, sınıfı, persistence "
    "durumu ve AI yorumu."
)


# ============================================================================
# Yardımcı fonksiyonlar
# ============================================================================
def _utpm_color(class_idx):
    """Jenks 5-sınıf rengi."""
    colors = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
    if class_idx is None or class_idx < 0:
        return "#cccccc"
    return colors[min(int(class_idx), 4)]


# ============================================================================
# Veri yükleme (cached)
# ============================================================================
@st.cache_data
def _load():
    return load_all_data()


with st.spinner("Veriler yükleniyor..."):
    data = _load()

utpm = data["utpm"]
boundary = data["boundary"]


# ============================================================================
# Yan panel — API key + ayarlar
# ============================================================================
with st.sidebar:
    st.header("⚙️ Ayarlar")

    # API key — secrets veya env
    default_key = ""
    try:
        default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass
    if not default_key:
        default_key = os.environ.get("ANTHROPIC_API_KEY", "")

    api_key = st.text_input(
        "Anthropic API key (opsiyonel)",
        value=default_key,
        type="password",
        help="Boş bırakırsanız template-based yorum kullanılır.",
    )

    radius_m = st.slider(
        "Komşuluk yarıçapı (m)",
        min_value=100, max_value=1500, step=100, value=500,
    )

    st.markdown("---")
    st.markdown("**Veri özeti**")
    st.metric("Toplam hücre", f"{len(utpm):,}")
    st.metric("Pilot alan", "25.4 km²")

    if st.button("🔄 Cache temizle"):
        st.cache_data.clear()
        st.rerun()


# ============================================================================
# Harita — UTPM choropleth + tıklama
# ============================================================================
col_map, col_info = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ UTPM Skoru Haritası")

    # Folium harita için merkezi koordinat al
    boundary_4326 = boundary.to_crs("EPSG:4326")
    centroid = boundary_4326.geometry.unary_union.centroid

    m = folium.Map(
        location=[centroid.y, centroid.x],
        zoom_start=13,
        tiles="CartoDB positron",
    )

    # Pilot sınır overlay
    folium.GeoJson(
        boundary_4326.to_json(),
        name="Pilot sınır",
        style_function=lambda x: {
            "fillColor": "#ffffff", "color": "#0a9376",
            "weight": 2, "fillOpacity": 0.0,
        },
    ).add_to(m)

    # UTPM choropleth — sade hızlı render için sample ile
    @st.cache_data
    def _utpm_geojson():
        utpm_4326 = utpm[["cell_id", "utpm_score", "utpm_class", "lisa_cluster", "geometry"]].to_crs("EPSG:4326")
        return utpm_4326.to_json()

    folium.GeoJson(
        _utpm_geojson(),
        name="UTPM",
        style_function=lambda feat: {
            "fillColor": _utpm_color(feat["properties"]["utpm_class"]),
            "color": "transparent", "fillOpacity": 0.55,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["cell_id", "utpm_score", "lisa_cluster"],
            aliases=["Hücre:", "UTPM:", "Cluster:"],
            sticky=True,
        ),
    ).add_to(m)

    folium.LayerControl().add_to(m)

    # Streamlit-folium tıklama
    out = st_folium(m, height=500, width=None,
                    returned_objects=["last_clicked"])


# ============================================================================
# Tıklanan hücrenin paneli
# ============================================================================
clicked = out.get("last_clicked") if out else None

with col_info:
    st.subheader("📍 Seçilen hücre")

    if clicked is None:
        st.info("Haritaya tıklayın → hücre detayları burada görünecek.")
    else:
        lat, lon = clicked["lat"], clicked["lng"]
        cell_row = find_cell_by_coords(lat, lon, utpm)

        if cell_row is None:
            st.warning(f"Pilot alan dışı: ({lat:.5f}, {lon:.5f})")
        else:
            cid = cell_row["cell_id"]
            summary = cell_summary(cid, data)
            comparison = neighborhood_comparison(cid, data, radius_m=radius_m)

            # Üst metrikler
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("UTPM skoru", f"{summary['utpm_score']:.1f}")
            mc2.metric("LST (5y med)",
                        f"{summary['lst_mean']:.2f} °C" if summary.get('lst_mean') else "?")
            mc3.metric("Sınıf", summary["utpm_class_label"])

            # LISA
            lisa = summary["lisa_cluster"]
            lisa_emoji = {"HH": "🔴", "LL": "🔵", "HL": "🟠",
                          "LH": "🟦", "NS": "⚪"}.get(lisa, "")
            st.markdown(f"**LISA:** {lisa_emoji} `{lisa}` — _{summary['lisa_description']}_")

            # Persistence
            if "persistence" in summary:
                p = summary["persistence"]
                st.markdown("**Persistence (5 yıl)**")
                p1, p2 = st.columns(2)
                p1.metric("Yıllık ortalama", f"{p['yearly_mean_lst']:.2f} °C"
                          if p['yearly_mean_lst'] else "?")
                p2.metric("Q4 yıl sayısı", f"{p['years_in_top_quartile']}/5")

            # Komşuluk
            if comparison:
                st.markdown(f"**Komşuluk** (r={radius_m} m, n={comparison['n_neighbors']})")
                c1, c2 = st.columns(2)
                c1.metric("Komşu medyan UTPM", f"{comparison['neighbor_median_utpm']:.1f}")
                c2.metric("Fark (vs)",
                            f"{comparison['vs_neighborhood']:+.1f}",
                            delta_color="inverse")

            # Feature değerleri
            if "features" in summary:
                with st.expander("🧪 7 fiziksel değişken"):
                    feat_df = []
                    for k, v in summary["features"].items():
                        if v is not None:
                            feat_df.append({"Değişken": k, "Değer": f"{v:.3f}"})
                    if feat_df:
                        st.table(feat_df)

            # AI yorumu
            st.markdown("---")
            st.markdown("### 🤖 AI Yorumu")
            with st.spinner("Yorum oluşturuluyor..."):
                text, source = explain_with_claude(
                    summary, comparison,
                    api_key=api_key if api_key else None,
                )
            st.write(text)
            if source == "claude":
                st.caption("✓ Claude API")
            else:
                st.caption("⚠ Template fallback (Claude API key girin daha akıllı yorum için)")


# ============================================================================
# Alt metin
# ============================================================================
st.markdown("---")
st.caption(
    "Veri kaynakları: Landsat 8/9 LST 2020-2024 yaz medyan, Sentinel-2 NDVI/Albedo, "
    "ESA WorldCover 2021, OSM coastline + roads, GHSL 2018, Konyaaltı Belediyesi imar verileri. "
    "Random Forest 8 feature × 28,247 hücre."
)
