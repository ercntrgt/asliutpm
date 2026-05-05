# UTPM Konyaaltı

**Urban Thermal Persistence Model** — Antalya Konyaaltı için kentsel ısı kalıcılık tarama aracı. Doktora tezi araştırma altyapısı.

## Özet

30 m grid çözünürlüğünde Landsat yer yüzey sıcaklığını (LST) 7 mekânsal-morfolojik değişkenden Random Forest ile öğrenip, lineer bir kentsel ısı kalıcılık indeksi (0-100) üreten ve mekânsal otokorelasyonla doğrulayan model.

**Pilot alan:** 15 mahalle, 25.4 km² kentleşmiş sahil koridoru, 28,247 grid hücresi.

**Ana bulgular:**
- Random Forest in-distribution R² = **0.846** (RMSE 1.22 °C)
- Yıllar arası mekânsal LST korelasyonu mean = **0.905** (2020-2024)
- **Persistent HOT spots: 2,008 hücre** (5/5 yıl en sıcak quartile'da)
- Global Moran's I = **0.738** (p < 0.001) → güçlü mekânsal kümeleme
- LISA HH cluster: **5,181 hücre** (UHI çekirdeği), LL: 5,860 (serin küme)
- Jenks 5 sınıf: **881 hücre "Çok sıcak"** (acil müdahale alanı)

## Kurulum

```bash
conda env create -f environment.yml
conda activate utpm
pip install -e .
```

VS Code: sağ alttaki Python yorumlayıcısını `utpm` ortamına çevirin.

## Yapı

- `data/` — Ham + işlenmiş veriler (büyük dosyalar `.gitignore`'da)
- `notebooks/` — Sıralı analiz notebook'ları (00 → 10)
- `src/` — 11 Python modülü (yeniden kullanılabilir paket)
- `tests/` — pytest unit testler
- `streamlit_app/` — Karar destek web uygulaması
- `tez/` — Yönetici özeti, yöntem, sonuçlar, sınırlılıklar, öneriler
- `results/` — RF model + validation JSON
- `figures/` — 18 görsel
- `tables/` — 13 özet CSV

## Notebook akışı

```
00_data_overview        →  imar Excel keşfi + DMS parse
01_grid_setup           →  pilot sınır + 30m + 100m grid
02_lst                  →  Landsat LST kompoziti (GEE)
03_variables            →  NDVI + Albedo + Impervious (GEE)
04_building_height      →  imar + buffer cascade imputation
05_dtc_breeze           →  OSM coastline + ray casting + yol
06_standardization      →  log + z-score
07_multicollinearity    →  VIF analizi (multicollinearity yok)
08_rf_model             →  RF + 4 validation katmanı
09_cross_year_validation →  5 yıl × persistence
10_shap_utpm            →  SHAP + UTPM + Moran/LISA + Jenks
```

## Çalışma alanı

15 mahalleli kentleşmiş sahil koridoru: UNCALI, ULUÇ, HURMA, MOLLA YUSUF, ÖĞRETMENEVLERİ, TOROS, SİTELER, LİMAN, GÜRSU, ARAPSUYU, KUŞKAVAĞI, PINARBAŞI, AKKUYU, ALTINKUM, SARISU.

CRS: EPSG:32636 (WGS84 / UTM Zone 36N).

## Veri ön-koşulları

1. `data/raw/konyaalti_imar_tum_veri.xlsx` — pilot imar verisi (manuel yerleştirme)
2. Google Earth Engine kimlik doğrulama:
   ```powershell
   [Environment]::SetEnvironmentVariable('GEE_PROJECT', 'asliutpm', 'User')
   ```
   Notebook 02'de `ee.Authenticate()` ilk çalıştırma.

## Test

```bash
pytest tests/
```

DMS koordinat parser için 11 unit test.

## Karar destek aracı

```bash
conda activate utpm
cd streamlit_app
streamlit run app.py
```

Browser'da `localhost:8501`. Haritaya tıklayarak hücre detayları + AI yorumu (Claude API opsiyonel).

## Tez metni materyalleri

`tez/` klasöründe:

- `01_executive_summary.md` — yönetici özeti, sayısal bulgular
- `02_methodology.md` — 16 haftalık pipeline + akış şeması
- `03_results.md` — kapsamlı sayısal sonuç tabloları
- `04_limitations.md` — 10 sınırlılık + hafifletme önerileri
- `05_recommendations.md` — şehir planlamacısına öneri belgesi
- `06_figures_tables_index.md` — 18 görsel + 13 tablo + 7 GPKG indeksi

## Lisans

Akademik araştırma — Doktora tezi.

## Repo

GitHub: https://github.com/ercntrgt/asliutpm
