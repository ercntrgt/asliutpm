# Hafta 24 — Spatial Lag Feature Denemesi: Hedef Sızıntısı (Target Leakage) Bulgusu

## Motivasyon

Hafta 23'te kritik akademik sınırlılık tespit edildi: **RF residuals'ında mekânsal otokorelasyon (Moran I = 0.6552, p<0.001)**. Bu, modelimizin pilot bölgenin mekânsal yapısının önemli bir kısmını yakalayamadığını gösterdi (L13).

Behrens & Schmidt (2018) literatüründen ilham alarak **spatial lag feature** (8-en-yakın-komşu LST ortalaması) eklemeyi denedik.

## Yöntem

### spatial_lag_lst hesaplama

```python
def spatial_lag_lst(grid, lst_col="lst_mean", k=8, exclude_self=True):
    centroids = np.column_stack([grid.geometry.centroid.x, grid.geometry.centroid.y])
    tree = cKDTree(centroids)
    _, idx = tree.query(centroids, k=k+1)  # +1: kendisi dahil
    if exclude_self:
        idx = idx[:, 1:]                    # ilk sütun (kendisi) at
    return grid[lst_col].to_numpy()[idx].mean(axis=1)
```

8 minimal feature seti:
- ndvi, albedo, dw_built, building_height, road, dtc_breeze, wind_blockage, **spatial_lag_lst**

### Pipeline

- 5-seed × 5-fold CV (Hafta 22 protokolü)
- VIF kontrolü
- Residual Moran's I (kritik test)
- SHAP global importance

## Sonuçlar

### Görünüşte Müthiş İyileşme

| Metrik | Hafta 22 (7 feat) | Hafta 24 (8 feat, lag) | Δ |
|---|---|---|---|
| R² (CV mean) | 0.8698 ± 0.0057 | **0.9936** ± 0.0003 | **+0.124** |
| RMSE | 1.124 °C | **0.250** °C | -0.874 |
| **Residual Moran I** | (Hafta 23: 0.6552) | **0.1030** | **-84.3%** |
| UTPM × LST r | 0.4948 | **0.9933** | +0.498 |
| UTPM Moran I | 0.801 | 0.989 | +0.188 |

CV CI95 daraldı: [0.9934, 0.9937] — sayısal güven artışı.

### ⚠ Ancak: Hedef Sızıntısı (Target Leakage)

**`spatial_lag_lst × LST` Pearson r = 0.996** (autocorrelation gücü)

**SHAP global importance yeni:**

```
spatial_lag_lst         0.936  ⭐ %93.6
ndvi_mean               0.017  %1.7
dtc_breeze_m            0.014  %1.4
dw_built_pct            0.012  %1.2
albedo_mean             0.011  %1.1
wind_blockage_index     0.004  %0.4
road_density            0.004  %0.4
building_height_mean    0.001  %0.1
```

**Model neredeyse tamamen tek bir feature'a (spatial_lag_lst) bağlı**. Diğer 7 feature toplam %6.4 katkı veriyor.

## Akademik Yorum

### Bu Bir Hedef Sızıntısı (Target Leakage)

Spatial_lag_lst, hücrenin **komşu LST'lerinin ortalaması**. LST mekânsal olarak çok düzgün (autocorrelation r=0.996) → komşu LST'yi biliyorsan kendi LST'yi büyük doğrulukla tahmin edersin.

**Klasik literatür kavramları:**
1. **Information leakage** — target değişkenin ham bir formu feature olarak modele giriyor (Provost & Fawcett 2013)
2. **Spurious skill** — model R²'si gerçek prediktiv güçten değil, target proxy'sinden geliyor
3. **Train-test contamination** — k-fold CV'de train fold hücrelerinin LST'leri test fold hücrelerinin spatial_lag'ine etki ediyor

### Pratik Sonuç: Bu Model Üretim Sürecinde Kullanılamaz

- **Yeni bir hücre için tahmin yapmak istiyoruz** (örn. yeni bir mahalle, ya da gelecek yıl)
- O hücrenin komşu LST'leri **zaten biliniyor olmalı** ki modele girdi olarak verilsin
- Eğer komşu LST'ler biliniyorsa, **kendi LST'sini hesaplama ihtiyacı yoktur** (interpolation yapılabilir doğrudan)
- Yani model "predict before you know" probleminde işe yaramaz

### "Out-of-time" Test Spatial Lag İçin Bile Çalışmaz

Hafta 23'te 2020-2023 train + 2024 test yapıldı (R²=0.917). Spatial lag kullanılırsa bu test bile **leakage**:
- Test 2024 hücrelerinin komşuları aynı set içinde 2024 değerleri
- Doğru spatial CV: leave-one-block-out **+ block-içinde** spatial_lag_lst yeniden hesap (ki o train block'taki LST'lerle)

Bu kompleks revizyon yapılmadı — bu **L14 yeni sınırlılık** olarak tezde rapor edilir.

## Karar — Akademik Dürüstlük

**Hafta 22 7-feature minimal model PRODUCTION MODELİ olarak kabul edilir.**

| Karşılaştırma | Hafta 22 | Hafta 24 |
|---|---|---|
| R² | 0.870 | 0.994 |
| RMSE | 1.12 °C | 0.25 °C |
| Akademik geçerlilik | ✅ Dürüst | ❌ Target leakage |
| Production | ✅ Kullanılabilir | ❌ "Predict before you know" |
| Tezde | **Ana model** | **Demo: leakage uyarısı** |

### L13 Sınırlılığı: Hala Açık

Sayısal olarak Hafta 24 residual Moran I = 0.103 → görünüşte L13 kapanır. **Ama bu sayı** spatial_lag_lst data leakage'ı sayesinde elde edildi. L13 (residuals mekânsal otokorelasyona sahip) **akademik anlamda hala açık**.

**Gerçek çözüm:**
- **Geographically Weighted Random Forest (GWRF)** — Quiñones et al. (2021)
- **RF-kriging hibrit** — RF tahmin + residual kriging
- **Nested spatial CV** — fold içi spatial_lag yeniden hesap

Bu yaklaşımlar bu çalışmanın kapsamı dışında bırakıldı, **sonraki çalışma alanı** olarak tezde önerilir.

## Üretilen Dosyalar (Demo Olarak)

- `data/processed/grid_30m_full.gpkg` — `spatial_lag_lst` kolonu eklendi
- `data/processed/grid_30m_modeling.gpkg` — 8-feature
- `data/processed/grid_30m_predictions.gpkg` — Hafta 24 modeli ile yeni residuals
- `data/processed/grid_30m_utpm.gpkg` — Hafta 24 modeli ile yeni UTPM (uyarı: spurious güçlü)
- `results/rf_model.pkl` — 8-feature RF (1.2 GB local)
- `results/rf_validation.json`, `results/utpm_analysis.json`, `results/shap_values.npy`
- `tables/19_spatial_rf_comparison.csv` — Hafta 22 vs Hafta 24 karşılaştırma
- `src/spatial_features.py` — `spatial_lag_lst`, `spatial_lag_generic` fonksiyonları
- `src/config.py` — `MINIMAL_FEATURES` (8 feature liste)

## Production Modeli Geri Yükleme

Production'da Hafta 22 modelini kullanmak istersen:

```bash
# Hafta 23 commit'ten model geri yükle
git checkout 1269e5a -- results/rf_model.pkl
git checkout 1269e5a -- data/processed/grid_30m_predictions.gpkg
git checkout 1269e5a -- data/processed/grid_30m_utpm.gpkg
```

Veya Hafta 22'deki 7-feature minimal pipeline'ı yeniden koştur.

## Tezsel Hikaye

Bu hafta **negatif sonuç değil, pedagojik kazanım**:

1. **Naïf yaklaşım göstermeli (Hafta 24):** "Spatial lag eklersek R² 0.99 olur, ne kötüsü olabilir?"
2. **Target leakage'i teşhis etmeli (bu rapor):** "SHAP %93 spatial_lag → bu legit feature değil, target proxy"
3. **Doğru yöntemi önermeli (sonraki çalışma):** GWRF, RF-kriging, nested spatial CV

Bu hikaye **akademik dürüstlüğün** ve **eleştirel düşünmenin** doktora tezindeki yerini gösterir.

## Yeni Sınırlılık L14

**L14: Spatial lag pure-out-of-sample test edilmedi.** Mevcut implementasyon tüm grid'de hesaplandı (data leakage). Production için fold-içi yeniden hesaplama gerekir. Bu da yapılırsa muhtemelen Hafta 22 R²=0.87 değerine yakın bir sonuç verir, çünkü gerçek mekânsal yapı 7 feature'la zaten yakalanmış.

## Sonraki Çalışma

1. **Nested spatial CV ile spatial_lag_lst yeniden test** — fold-içi hesap, gerçek out-of-sample R²
2. **GWRF (Quiñones et al. 2021)** — yerel parametreli RF, mekânsal heterojeniteyi yakalar
3. **RF-kriging hibrit (Hengl et al. 2018)** — RF tahmin + residual kriging
