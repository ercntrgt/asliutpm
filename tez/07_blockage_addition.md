# Hafta 17 — Wind Blockage Index Eklemesi

## Motivasyon

İlk DTC_breeze formülasyonu (Hafta 6) saf geometrik Öklid mesafe esaslıydı: hücre centroid'inden hakim rüzgar yönüne (165° SSE) bir ışın çekilip OSM kıyı çizgisi ile ilk kesişim mesafesi hesaplanıyordu. Bu yaklaşım, **bina yüksekliği veya morfolojik blokaj etkisini hesaba katmıyordu**.

Kentsel klimatoloji literatüründe bilinen bir gerçek: kentin iç bölgelerinde yüksek binalar **rüzgar erişimini bloklar**, sokak vadileri (street canyon) yüzey rüzgarını yavaşlatır. Oke (1987), Grimmond & Oke (1999), Stewart & Oke (2012, Local Climate Zones) bu etkiyi `surface roughness length`, `frontal area index`, ve `sky view factor` parametreleriyle modeller.

## Yöntem

`wind_blockage_index` feature'ı eklendi. Algoritma:

```
Her hücre c için:
    Ray ← centroid(c) noktasından 165° SSE yönünde 20 km uzunlukta ışın
    n_samples = 50 nokta ışın boyunca eşit dağıtılır
    Her sample noktası için:
        En yakın grid hücresinin building_height_mean değeri okunur (cKDTree)
        Mesafe-decay ağırlığı: w(d) = 1 - d / 20km
    blockage(c) = Σ(height × weight) / n_samples
```

Yakın binalar daha çok engelliyor (mesafe-decay). Sample sayısı 50 → ortalama 400 m aralık (28K hücre × 50 sample × cKDTree.query → 6.5 saniye, vectorized).

## Kontrol — Multicollinearity Yok

| Korelasyon | r |
|---|---|
| blockage × LST | +0.153 |
| blockage × DTC_breeze | -0.004 (bağımsız bilgi!) |
| blockage × building_height_mean | +0.588 |

**VIF analizi:**

| Feature | VIF |
|---|---|
| impervious_pct_z | 1.78 |
| **wind_blockage_index_z** | **1.52** |
| albedo_mean_z | 1.45 |
| building_density_per_km2_z | 1.33 |
| ndvi_mean_z | 1.30 |
| dtc_breeze_m_z | 1.29 |
| road_density_z | 1.20 |
| building_height_z | 1.08 |

VIF < 2 → multicollinearity yok. Yeni feature **bağımsız bilgi** taşıyor.

## RF Karşılaştırma

| Metrik | Önce (8 feature) | Sonra (9 feature) | Δ |
|---|---|---|---|
| Random 5-fold CV R² | 0.846 | **0.850** | +0.004 |
| Random CV RMSE | 1.221 °C | 1.204 °C | -0.017 |
| Spatial Block CV R² | 0.720 | **0.724** | +0.004 |
| Hold-out R² | 0.105 | 0.094 | -0.011 |
| Permutation null 99p | -0.061 | -0.057 | ≈ |
| UTPM × LST r | 0.371 | **0.383** | +0.012 |
| Moran's I | 0.738 | 0.740 | ≈ |
| Çok sıcak (Jenks 5) | 881 hücre | **973 hücre** | +92 |
| LISA HH cluster | 5,181 | 5,263 | +82 |
| LISA LL cluster | 5,860 | 6,216 | +356 |

**Yorum:** İyileşme küçük ama tutarlı — Random/Spatial CV/UTPM hepsi aynı yönde ilerliyor. Hold-out hafifçe düştü, ama bu varyans aralığında (Hafta 10 zaten R²=0.10 idi).

## Permutation Importance (yeni 9 feature)

```
ndvi_mean             0.407   (1. — non-lineer NDVI hala dominant)
albedo_mean           0.329
dtc_breeze_m          0.274
impervious_pct        0.124
wind_blockage_index   0.062   ⭐ YENİ — building_height ve density'den daha önemli
is_dtc_saturated      0.044
road_density          0.032
building_height_mean  0.009
building_density      0.004
```

## SHAP Importance (yeni 9 feature)

```
albedo_mean           0.354
ndvi_mean             0.258
dtc_breeze_m          0.168
impervious_pct        0.090
wind_blockage_index   0.061   ⭐ 5. sırada
road_density          0.036
building_height_mean  0.014
building_density      0.010
is_dtc_saturated      0.010
```

**Önemli bulgu:** Wind blockage index hem permutation hem SHAP'ta **building_height (%3) ve building_density (%1)'den daha önemli**. Bu, modelin "bina yüksekliği" yerine "rüzgar yönündeki bina yüksekliği" sinyalini daha bilgilendirici bulduğunu gösteriyor.

## LISA Cluster Değişimi

| Cluster | Önce | Sonra | Δ |
|---|---|---|---|
| HH | 5,181 | **5,263** | +82 |
| LL | 5,860 | **6,216** | +356 |
| HL | 146 | 146 | 0 |
| LH | 141 | 126 | -15 |
| NS | 16,919 | 16,496 | -423 |

LL cluster (serin küme) %6 büyüdü — wind blockage index NS olan bazı hücrelerde belirleyici sinyal verince LL'e dönüştü. UHI çekirdeği (HH) az değişti.

## Tezsel Katkı

1. **Literatür-uyumu:** Oke (1987) urban canopy theorisi ile birinci derece konsisten — yüksek bina çevresi LST artışı modelde temsil edildi.
2. **Feature mühendisliği:** Bina yüksekliğini "hücre içi" değil "rüzgar boyunca" özetleyen yeni bir feature.
3. **Gerçekçi UHI:** Pilot bölgenin iç-kara kuzey kesimindeki "engellenmiş" hücreler, salt DTC mesafesinden bağımsız bir blokaj sinyali aldı.

## Sınırlılık (devam)

Wind blockage **yön sabit 165°**. ERA5 ile saatlik kalibrasyon hala yapılmadı (Sınırlılık L8). Ek olarak:

- **Bina genişliği yok** (sadece yükseklik) — frontal area index (FAI) hesaplanmadı
- **Sky view factor** modelde değil
- **Surface roughness length z₀** hesaplanmadı
- **Sokak yön bilgisi** (yön ile yapı sırası) modelde değil

## Sonraki Çalışmalar

1. ERA5 ile rüzgar yönü kalibrasyonu (saatlik öğle dağılımı)
2. Frontal Area Index — bina genişlik × yükseklik
3. Sky View Factor — UMEP veya QGIS LCZ tooling ile
4. Sokak yönü (azimuth) ile rüzgar yönü uyum analizi
