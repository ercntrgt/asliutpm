# UTPM Konyaaltı

Antalya Konyaaltı için kentsel ısı kalıcılık modeli (Urban Thermal Persistence Model). Doktora tezi araştırma altyapısı.

## Kurulum

```bash
conda env create -f environment.yml
conda activate utpm
pip install -e .
```

VS Code: sağ alttaki Python yorumlayıcısını `utpm` ortamına çevirin.

## Yapı

- `data/` — Veri (raw, processed, grid, external). Büyük dosyalar git'e gitmiyor.
- `notebooks/` — Sıralı analiz notebook'ları (`00_data_overview` → `01_grid_setup` → ...).
- `src/` — Yeniden kullanılabilir Python modülleri (`utpm` paketi olarak install edilir).
- `tests/` — pytest unit testler.
- `results/` — Modeller (`.pkl`) ve metrikler (`.csv`).
- `figures/` — Grafikler ve haritalar.
- `tables/` — CSV özet tablolar.
- `streamlit_app/` — Karar destek prototipi (Hafta 14+).

## Akış

1. `00_data_overview` — İmar verisi keşfi, koordinat parse, pilot alan filtresi
2. `01_grid_setup` — 30 m + 100 m grid sistemi
3. `02_lst` — Landsat LST kompoziti (Google Earth Engine)
4. `03_variables` — NDVI, Albedo, Geçirimsiz yüzey
5. `04_building_height` — Bina yüksekliği imputation (buffer cascade)
6. `05_dtc_breeze` — Rüzgar-yönelimli kıyı mesafesi
7. `06_standardization` — Z-skor + log dönüşümler
8. `07_multicollinearity` — VIF analizi
9. `08_rf_model` — Random Forest eğitimi
10. `09_validation` — 5 katmanlı doğrulama
11. `10_shap_pdp` — Yorumlanabilirlik
12. `11_utpm` — İndeks hesabı
13. `12_classification_maps` — Jenks sınıflama, haritalar

## Çalışma alanı

15 mahalleli kentleşmiş sahil koridoru:
UNCALI, ULUÇ, HURMA, MOLLA YUSUF, ÖĞRETMENEVLERİ, TOROS, SİTELER, LİMAN, GÜRSU, ARAPSUYU, KUŞKAVAĞI, PINARBAŞI, AKKUYU, ALTINKUM, SARISU.

CRS: EPSG:32636 (WGS84 / UTM Zone 36N).

## Veri ön-koşulu

`data/raw/konyaalti_imar_tum_veri.xlsx` dosyasını manuel olarak yerleştirin. Notebook 00 bu dosyaya bakar.

## Test

```bash
pytest tests/
```

## Lisans

Akademik araştırma — Doktora tezi.
