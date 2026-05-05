"""UTPM Karar Destek Asistanı — Streamlit (online deploy edilebilir).

30 m grid hassasiyet korunur. Folium PNG ImageOverlay → hızlı render
(28K poligon GeoJSON yerine 9 KB raster).

Çalıştırma (lokal):
    cd streamlit_app && streamlit run app.py

Deploy (Streamlit Community Cloud):
    Bkz: STREAMLIT_DEPLOY.md (repo root)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.utils import (  # noqa: E402
    load_all_data, find_cell_by_coords, cell_summary, neighborhood_comparison,
    JENKS_LABELS, LISA_DESCRIPTIONS, PRIORITY_DESCRIPTIONS,
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
    "Urban Thermal Persistence Model — 30 m grid çözünürlüklü kentsel ısı "
    "kalıcılık tarama aracı. Haritada bir noktaya tıklayın → o hücrenin "
    "UTPM skoru, sınıfı, persistence, AI yorumu."
)


# ============================================================================
# Veri yükleme (cached)
# ============================================================================
@st.cache_data
def _load():
    return load_all_data()


with st.spinner("Veri yükleniyor..."):
    data = _load()

grid = data["grid"]
boundary = data["boundary"]
bbox = data["bbox"]


# ============================================================================
# Yan panel
# ============================================================================
with st.sidebar:
    st.header("⚙️ Ayarlar")

    # API key
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
        help="Boş bırakırsanız kural-tabanlı yorum kullanılır.",
    )

    radius_m = st.slider(
        "Komşuluk yarıçapı (m)",
        min_value=100, max_value=1500, step=100, value=500,
    )

    show_lisa = st.checkbox(
        "LISA cluster katmanı göster (yavaş!)",
        value=False,
        help="HH/LL küme noktaları (~12K). Yavaşlatır.",
    )

    st.markdown("---")
    st.markdown("**Veri özeti**")
    st.metric("30 m hücre", f"{len(grid):,}")
    st.metric("Pilot alan", "25.4 km²")

    if st.button("🔄 Cache temizle"):
        st.cache_data.clear()
        st.rerun()


# ============================================================================
# Harita — PNG ImageOverlay + click handler
# ============================================================================
col_map, col_info = st.columns([2, 1])

with col_map:
    st.subheader("🗺️ UTPM Skoru Haritası (30 m)")

    # Merkez koordinat (bbox'tan)
    center_lat = (bbox["south"] + bbox["north"]) / 2
    center_lon = (bbox["west"] + bbox["east"]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
    )

    # PNG choropleth ImageOverlay (30 m piksel, instant render)
    folium.raster_layers.ImageOverlay(
        image=data["raster_path"],
        bounds=[[bbox["south"], bbox["west"]],
                [bbox["north"], bbox["east"]]],
        opacity=0.75,
        name="UTPM 5-sınıf",
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)

    # Pilot sınır (hafif)
    boundary_4326 = boundary.to_crs("EPSG:4326")
    folium.GeoJson(
        boundary_4326.to_json(),
        name="Pilot sınır",
        style_function=lambda x: {
            "fillColor": "transparent", "color": "#0a9396",
            "weight": 2, "fillOpacity": 0.0,
        },
    ).add_to(m)

    # Opsiyonel LISA katmanı
    if show_lisa:
        with st.spinner("LISA cluster yükleniyor..."):
            lisa_clusters = ("HH", "LL")
            lisa_subset = grid[grid["lisa_cluster"].isin(lisa_clusters)]
            lisa_4326 = lisa_subset[["cell_id", "lisa_cluster", "geometry"]].to_crs("EPSG:4326")
            folium.GeoJson(
                lisa_4326.to_json(),
                name="LISA HH/LL",
                style_function=lambda feat: {
                    "fillColor": "#d7191c" if feat["properties"]["lisa_cluster"] == "HH" else "#2c7bb6",
                    "color": "transparent",
                    "fillOpacity": 0.5,
                },
            ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    # Streamlit-folium tıklama
    out = st_folium(m, height=520, width=None,
                    returned_objects=["last_clicked"])

    # Renk lejantı
    st.markdown("""
    **Lejant (UTPM Jenks 5-sınıf):**
    🟦 Çok serin · 🟩 Serin · 🟨 Orta · 🟧 Sıcak · 🟥 Çok sıcak
    """)


# ============================================================================
# Tıklanan hücre paneli
# ============================================================================
clicked = out.get("last_clicked") if out else None

with col_info:
    st.subheader("📍 Seçilen hücre")

    if clicked is None:
        st.info("Haritaya tıklayın → 30 m hücre detayları burada.")
    else:
        lat, lon = clicked["lat"], clicked["lng"]
        cell_row = find_cell_by_coords(lat, lon, grid)

        if cell_row is None:
            st.warning(f"Pilot alan dışı: ({lat:.5f}, {lon:.5f})")
        else:
            cid = str(cell_row["cell_id"])
            try:
                summary = cell_summary(cid, data)
            except Exception as e:
                st.error(f"Hücre özeti alınamadı: {type(e).__name__}: {e}")
                summary = {}
            try:
                comparison = neighborhood_comparison(cid, data, radius_m=radius_m)
            except Exception as e:
                st.warning(f"Komşuluk karşılaştırması atlandı: {type(e).__name__}")
                comparison = {}

            # Üst metrikler
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("UTPM",
                        f"{summary['utpm_score']:.1f}" if summary.get("utpm_score") else "?")
            mc2.metric("LST 5y med",
                        f"{summary['lst_mean']:.2f} °C" if summary.get("lst_mean") else "?")
            mc3.metric("Sınıf", summary.get("utpm_class_label", "?"))

            if "mahalle" in summary:
                st.caption(f"📍 Mahalle: **{summary['mahalle']}** · cell `{cid}`")

            # LISA
            lisa = summary.get("lisa_cluster", "NS")
            lisa_emoji = {"HH": "🔴", "LL": "🔵", "HL": "🟠",
                           "LH": "🟦", "NS": "⚪"}.get(lisa, "")
            lisa_desc = summary.get("lisa_description", "")
            st.markdown(f"**LISA:** {lisa_emoji} `{lisa}` — _{lisa_desc}_")

            # Priority
            if "priority" in summary:
                pr = summary["priority"]
                priority_emoji = {
                    "1_ACIL_MUDAHALE": "🔴", "2_YUKSEK_ONCELIK": "🟠",
                    "3_SICAK_ACIK": "🟧", "4_BLOKLU_ORTA": "🟫",
                    "5_ORTA": "🟡", "6_ORTA_ACIK": "🟨",
                    "7_BLOKLU_SERIN": "🟢", "8_SERIN_ORTA": "🟩",
                    "9_KORUMA": "💚",
                }.get(pr["label"], "")
                pr_nice = pr["label"].split("_", 1)[1].replace("_", " ").title()
                st.markdown(f"**Karar Önceliği:** {priority_emoji} `{pr_nice}`")
                if pr.get("description"):
                    st.caption(f"_{pr['description']}_")
                if pr.get("wind_blockage_index") is not None:
                    st.caption(f"Wind Blockage Index: {pr['wind_blockage_index']:.3f}")

            # Persistence
            if "persistence" in summary:
                p = summary["persistence"]
                st.markdown("**5-yıl Persistence**")
                pc1, pc2 = st.columns(2)
                pc1.metric("Yıllık ort.",
                            f"{p['yearly_mean_lst']:.2f} °C" if p.get("yearly_mean_lst") else "?")
                pc2.metric("Q4 yıl sayısı",
                            f"{p.get('years_in_top_quartile', 0)}/5")

            # Komşuluk
            if comparison:
                st.markdown(f"**Komşuluk** (r={radius_m} m, n={comparison['n_neighbors']})")
                cc1, cc2 = st.columns(2)
                cc1.metric("Komşu med UTPM",
                            f"{comparison['neighbor_median_utpm']:.1f}")
                cc2.metric("Fark",
                            f"{comparison['vs_neighborhood']:+.1f}",
                            delta_color="inverse")

            # 7 fiziksel değişken (expander)
            if "features" in summary:
                with st.expander("🧪 7 fiziksel değişken"):
                    feat_rows = []
                    for k, v in summary["features"].items():
                        feat_rows.append({"Değişken": k, "Değer": f"{v:.3f}"})
                    if feat_rows:
                        st.table(feat_rows)

            # AI yorumu — her durumda görünsün (key varsa Claude, yoksa fallback template)
            st.markdown("---")
            st.markdown("### 🤖 AI Yorumu")
            text, source = "", "fallback"
            with st.spinner("Yorum oluşturuluyor..."):
                try:
                    text, source = explain_with_claude(
                        summary, comparison,
                        api_key=api_key if api_key else None,
                    )
                except Exception as e:
                    text = f"_(Yorum oluşturulamadı: {type(e).__name__}: {e})_"
                    source = "error"
            st.write(text)
            if source == "claude":
                st.caption("✓ Claude API ile gelişmiş yorum")
            elif source == "fallback":
                st.caption("ℹ Kural-tabanlı yorum — daha akıllı yorum için yan panele Anthropic API key girin")
            else:
                st.caption("⚠ Yorum motoru hata verdi")


# ============================================================================
# Alt
# ============================================================================
st.markdown("---")
st.caption(
    "Veri kaynakları: Landsat 8/9 LST 2020-2024 yaz medyan, Sentinel-2 NDVI/Albedo, "
    "Google Dynamic World, OSM, Konyaaltı imar verisi. "
    "Random Forest 7-feature minimal model (R²=0.870, RMSE 1.12°C). "
    "Github: github.com/ercntrgt/asliutpm"
)
