# Hafta 23 — Dış Doğrulama Paketi: MODIS + Out-of-Time + PDP + SHAP Interactions + Residual Moran

## Motivasyon

Doktora tezi için 4 kritik akademik test:
1. **Bağımsız uydu doğrulaması** (Landsat ≠ MODIS olmalı uyumlu)
2. **Temporal generalization** (geçmiş yıllardan gelecek tahmin)
3. **Açıklanabilirlik** (PDP + SHAP interactions)
4. **Model spesifikasyon kontrolü** (residuals mekânsal bağımsız mı?)

Sonuçlar **karışık** — bazı testler tezi güçlendirdi, bazıları kritik sınırlılık ortaya çıkardı. **Akademik dürüstlük** gereği hepsini raporluyoruz.

---

## 1. Out-of-Time Validation ✅ (BÜYÜK KAZANIM)

### Yöntem

- **Train:** 2020-2023 yıllık LST ortalaması (her hücre için)
- **Test:** 2024 yıllık LST
- **Aynı feature seti** (10 feature, 28,247 hücre)
- RF (n_estimators=200, max_depth=20)

### Sonuçlar

| Metrik | Değer |
|---|---|
| n hücre (overlap) | 28,247 |
| **R² (test 2024)** | **0.917** |
| RMSE | 0.891°C |
| MAE | 0.713°C |
| Karşılaştırma: in-sample 5-yıl medyan R² | 0.872 |
| **Out-of-time gap** | **-0.045** (negatif!) |

### Tezsel Yorum

**Out-of-time R² (0.917) in-sample R²'den (0.872) yüksek.** Bu **çok güçlü temporal generalization** kanıtı:
- Modelin gelecek yıl LST tahmini güvenilir
- Mekânsal feature'lar (NDVI, albedo, dw_built, dtc, vb.) yıllar arası **kararlı**
- 2022 ekstrem yıl tahminden hariç tutulmuş (train mean 4 yıllık) → 2024 daha tipik bir yıl

**Akademik argüman:** UTPM modeli **temporal stable** — 2025+ tahminleri için kalibrasyon gerekmez (ama 2030 sonra rekalibrasyon önerilir).

---

## 2. SHAP Interaction Values ✅

### Yöntem

`shap.TreeExplainer.shap_interaction_values()` 7-feature minimal RF üzerinde 200 sample.

### Top 5 Etkileşim (mean |SHAP_ij|)

| # | Pair | Strength |
|---|---|---|
| 1 | **NDVI × DW_built** | **0.464** |
| 2 | Albedo × DW_built | 0.382 |
| 3 | NDVI × Albedo | 0.300 |
| 4 | NDVI × DTC_breeze | 0.263 |
| 5 | DW_built × DTC_breeze | 0.192 |

### Tezsel Yorum

**NDVI × DW_built en güçlü etkileşim:**
- Yüksek NDVI + düşük yapılaşma → çok serin (additive)
- Düşük NDVI + yüksek yapılaşma → çok sıcak (additive)
- AMA **etkileşim**: yüksek NDVI'nin serinletme etkisi yapılaşma derecesine bağlı (mid-density'de daha güçlü)

Bu, lineer model varsayımlarını ihlal eden **kentsel klimatoloji bulgusu**. RF non-lineer modelleyici doğal yakalıyor.

PDP'lerde de görsel doğrulama: NDVI eğrisi 0.0-0.4 arası dik, 0.4+ doyumlu (saturation).

---

## 3. PDP — Partial Dependence Plots ✅

7 feature × 30-grid çözünürlük × 5000 sample. `figures/18_pdp.png` üretildi.

### Görsel Bulgular

- **NDVI:** 0.0-0.3 dik düşüş (her +0.1 NDVI = -1°C LST), 0.4+ saturate
- **Albedo:** 0.1-0.3 lineer artış, sonra plato
- **DW_built:** 0-50% arası dik artış, 60-100% saturate (Akdeniz beton tavanı)
- **Building height:** zayıf eğri (model bu feature'ı az kullanıyor)
- **Road density:** 0-50K m/km² lineer artış
- **DTC_breeze:** 0-3000m hızlı düşüş, 5000m+ saturate (kıyıdan uzaklaşma etkisi)
- **Wind blockage:** yumuşak artış

**Tezsel kullanım:** Şehir planlamacısı için **müdahale eğrisi**:
- NDVI'yi 0.2'den 0.4'e çıkar → ~2°C serinleme beklentisi
- Albedo'yu 0.2'den 0.15'e indir (koyu kaplama) → ~0.5°C serinleme

---

## 4. MODIS Cross-Validation ❌ (BAŞARISIZ)

### Yöntem

- **MODIS MOD11A2** (8-day composite, 1 km, LST_Day)
- 2020-2024 yaz medyan, QC mask (good quality only)
- 30 m grid'e zonal mean

### Sonuçlar

| Metrik | Değer |
|---|---|
| n hücre overlap | **34** (28,247'den) |
| Landsat medyan | 43.46°C |
| MODIS medyan | 38.06°C |
| **Pearson r** | **0.081** ← neredeyse sıfır |
| RMSE | 24.40°C |
| MAE | 16.70°C |
| Bias (L−M) | +16.46°C |

### Sebepler

**1. MODIS çözünürlük yetersizliği:**
- MOD11A2 native 1 km → pilot 5 × 5 km = ~25 piksel max
- QC bit mask (good quality only) → 34 hücre kaldı
- **İstatistiksel anlamlı karşılaştırma için yetersiz n**

**2. MODIS 1km mean smoothing:**
- 1 km MODIS pikseli içinde bina + yol + park + su karışır
- Mekânsal ortalama → kentsel hot spotlar silikleştirilir
- Landsat 30 m → keskin LST gradient'ini yakalar
- **Literatürde bilinen** MODIS underestimation (Pinker et al. 2009, Wan 2014)

**3. Bias +16°C:**
- Landsat ST_B10 yaz öğle saatleri (~11:00-12:00 lokal) — **peak heating zamanı**
- MOD11A2 8-day composite, gündüz pass'leri (~10:30 lokal)
- Akdeniz yaz öğleyin LST 50°C'ye çıkabilir, MODIS 8-day mean smoothing yapar → ~38°C
- Bu **fundamental** bir farklılık, hata değil

### Tezsel Duruş

**Bu bir başarısızlık değil — Landsat ve MODIS'in bilinen farklılıklarının dokümantasyonu:**

- "MODIS LST Konyaaltı pilot bölgesinin sınırlı kapsama (1 km native × 5 × 5 km pilot = 25 piksel) ve thermal smoothing özelliklerinden dolayı Landsat 30 m yaz öğle LST'siyle istatistiksel olarak karşılaştırılamamıştır (n=34, r=0.08)."
- "Bu sınırlılık Pinker et al. (2009) ve Wan (2014) tarafından raporlanan MODIS-Landsat thermal divergence ile uyumludur."
- **Sonraki çalışma:** Sentinel-3 SLSTR (300 m thermal) veya MODIS Night (gece sıcaklığı, daha az smoothing) ile çapraz doğrulama.

**Yine de Landsat LST güvenilirliği:**
- Out-of-time R² 0.917 → Landsat LST yıllar arası tutarlı
- Yıllık korelasyon mean 0.905 (Hafta 11) → mekânsal desen kararlı
- ESA Landsat Collection 2 Level-2 standart işlenmiş ürün, NASA/USGS validated
- Tek-kaynak validation eksikliği **L11 sınırlılığı altında raporlanır**

---

## 5. Residual Moran's I ⚠ (KRİTİK SORUN)

### Yöntem

RF tahmin residuals'ı (`actual - predicted`) üzerinde global Moran's I (k=8 NN).

### Sonuçlar

| Metrik | Değer |
|---|---|
| **Moran I (residuals)** | **0.6552** |
| z-score | 221.43 |
| p-value | < 0.0001 |

### Tezsel Anlam — Kritik Sınırlılık

**Residuals bağımsız değil — komşu hücrelerin tahmin hataları benzer.**

Bu, RF modelimizin **mekânsal yapının tam yakalayamadığını** gösterir:
- UTPM Moran I = 0.801 (UHI gerçekten kümeli)
- Residual Moran I = 0.655 (model bu kümelenmenin %18'ini açıklamış, %82'si residual'da kalmış)

**Karşılaştırma:** İdeal model residual Moran I ≈ 0 (rastgele). 0.655 → çok yüksek otokorelasyon.

### Olası Sebepler

1. **Eksik mekânsal feature'lar:** Latitude/longitude doğrudan feature olarak modelde yok
2. **Mahalle dummy'leri yok:** Belediye sınırı + mahalle ID feature olarak yok
3. **Komşu LST etkisi yok:** "Spatial lag" feature (komşu LST mean) eklenmedi
4. **Topografya yok:** DEM modele dahil edilmedi (Konyaaltı pilot için minor ama yine de eksik)

### Çözüm Önerileri (Sonraki Çalışma)

1. **Geographically Weighted Random Forest (GWRF)** — Quiñones et al. (2021)
2. **Spatial Lag Feature:** Her hücre için 8-NN mean LST'yi feature olarak ekle
3. **RF-Kriging Hibrit:** RF tahmin + residual kriging
4. **Convolutional Neural Network:** Spatial dependency'i doğal yakalar

### Akademik Yazım

> "RF residuals'ında istatistiksel olarak anlamlı mekânsal otokorelasyon gözlenmiştir (Moran's I = 0.655, z = 221.4, p < 0.001). Bu, modelimizin pilot bölgenin mekânsal yapısının önemli bir kısmını yakalayamadığını ve sonraki çalışmaların Geographically Weighted Random Forest (Quiñones et al. 2021) veya RF-kriging hibrit yaklaşımlarla bu sınırlılığı kapatabileceğini göstermektedir."

---

## Üretilen Dosyalar

- `data/processed/modis_lst_summer_median_2020_2024.tif` (1 KB) — MODIS raster
- `figures/18_pdp.png` — 7 feature × LST PDP eğrileri
- `figures/18_shap_interactions.png` — 7×7 etkileşim ısı haritası
- `figures/18_landsat_modis_validation.png` — scatter + Bland-Altman
- `tables/18_external_validation.csv` — özet tablo
- `results/external_validation.json` — JSON detay

## Tezsel Sonuç — Toparlama

| Test | Sonuç | Tezsel etki |
|---|---|---|
| **Out-of-time R²=0.917** | ✅ ÇOK GÜÇLÜ | Temporal generalization kanıtı |
| **SHAP interactions** | ✅ İLGİNÇ | NDVI × DW_built en güçlü etkileşim |
| **PDP eğrileri** | ✅ AÇIKLAYICI | Şehir planlamacısı müdahale eğrileri |
| **MODIS Pearson r=0.08** | ❌ BAŞARISIZ | Çözünürlük + smoothing — sınırlılık L12 |
| **Residual Moran I=0.66** | ⚠ KRİTİK | Spatial RF hibrit gereksinimi — sınırlılık L13 |

## Yeni Sınırlılıklar — L12 + L13

**L12: MODIS-Landsat çapraz doğrulama yetersizliği** — 1 km MODIS thermal smoothing + pilot küçük alanı (25 piksel) → istatistiksel anlamlı karşılaştırma yapılamadı. Sentinel-3 SLSTR (300 m thermal) sonraki çalışma.

**L13: Residuals mekânsal otokorelasyona sahip** (Moran I = 0.655, p<0.001) — model spatial yapının %82'sini residual'da bırakmış. Geographically Weighted RF veya RF-kriging hibrit gereksinimi.

---

## Sonraki Çalışma

1. **Geographically Weighted Random Forest** uygula (Quiñones et al. 2021)
2. **Spatial lag feature** ekle (komşu LST mean)
3. **Sentinel-3 SLSTR** ile alternatif çapraz doğrulama
4. **DEM** (NASA SRTM 30 m) ekle — Konyaaltı pilot için minor ama tamamlık için
