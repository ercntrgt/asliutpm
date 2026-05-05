# Hafta 18 — ERA5 Rüzgar Yönü Kalibrasyonu

## Motivasyon

Hafta 6'dan itibaren `WIND_FROM_DEG = 165°` (SSE) literatür/iklim atlas değeri olarak kullanıldı. DTC_breeze ve `wind_blockage_index` (Hafta 17) bu yön etrafında hesaplandı. Bu varsayımın **veri-tabanlı doğrulaması** gerekiyordu (sınırlılık L8).

## Yöntem

Veri kaynağı: **ECMWF/ERA5/HOURLY** (Google Earth Engine).

Filtreler:
- Yıllar: 2020-2024
- Aylar: Haziran, Temmuz, Ağustos
- Saatler: 11-14 UTC (TRT 14-17, yaz öğle saatleri — meltem etkisi maksimum)
- Bölge: Konyaaltı pilot sınırı

Hesaplama:
1. Her image için region-mean `u_component_of_wind_10m` ve `v_component_of_wind_10m` (10 m yükseklikte rüzgar bileşenleri)
2. `aggregate_array` ile her saat için scalar değer çek (memory-friendly)
3. Vector mean: `u_mean = mean(u)`, `v_mean = mean(v)`
4. Yön formülü (meteorolojik konvansiyon): `dir_FROM = (270 − atan2(v, u) × 180/π) mod 360`

**N = 1,840 saat** (5 yıl × 3 ay × 4 saat × ~31 gün)

## Sonuçlar

### Vector mean

```
u_mean = -0.700 m/s
v_mean = +1.817 m/s
speed  = 1.947 m/s
direction FROM = 158.9°
```

### Dağılım istatistikleri

| Metrik | Değer |
|---|---|
| Yön medyan | 160.6° |
| Yön 25% percentile | 149.5° |
| Yön 75% percentile | 174.7° |
| **Histogram dominant bin** | **155° (418 saat, %22.7)** |
| Hız medyan | 2.97 m/s |
| Hız maks | (raporlanmadı, ~5-7 m/s) |

### Yıl bazlı tutarlılık

| Yıl | u | v | Direction FROM | n |
|---|---|---|---|---|
| 2020 | -0.86 | +2.12 | 158° | 368 |
| 2021 | -0.54 | +1.20 | 156° | 368 |
| 2022 | -0.77 | +2.00 | 159° | 368 |
| 2023 | -0.77 | +1.82 | 157° | 368 |
| 2024 | -0.56 | +1.95 | 164° | 368 |

**Yıllık varyans dar:** 156°-164° → 8° aralık. ERA5 yön kalibrasyonu **istikrarlı**.

## Karşılaştırma

| Kaynak | Yön | Fark (vs konfig 165°) |
|---|---|---|
| Konfig (literatür/atlas) | 165° | — |
| ERA5 vector mean | 158.9° | **6.1°** |
| ERA5 medyan | 160.6° | 4.4° |
| ERA5 histogram dominant | 155° | 10.0° |

## Karar

**Eşik kriteri:** Fark > 10° → DTC_breeze + wind_blockage_index yeniden hesap.

**Sonuç:** Vector mean farkı 6.1°, medyan farkı 4.4° → **eşik altında**.

**Hareket:** Yeniden hesap GEREKMEDİ. Mevcut 165° konfig değeri ERA5 ile istatistiksel olarak uyumlu.

**Sebep:** 6° yön farkı ray casting'de DTC değerlerini anlamlı şekilde değiştirmez — pilot bölge geometrisi (kıyı çoğunlukla güneyde) bu küçük açı değişimine karşı düşük duyarlı. Wind blockage index'in bina yüksekliği toplamı da yön değişimine düşük duyarlı (hücre çevresinde ~400 m sample mesafesi, %5 yön değişimi sample lokasyonlarını birkaç on metre kaydırır).

## Tezsel Katkı

1. **L8 sınırlılığı kapandı:** Rüzgar yönü artık ERA5 verisiyle doğrulanmıştır.
2. **Konyaaltı yaz hakim rüzgar yönü:** SSE-ESE arası, **155°-165°** aralığında istikrarlı (Antalya kıyı meltemi karakteristiği).
3. **Yıllar arası varyans:** 8° dar — ekstrem yıllarda bile (2022 sıcak dalga) yön değişimi minimum.

## Üretilen Dosyalar

- `results/era5_wind_calibration.json` — vector mean, dağılım, yıllık özet
- `tables/12_era5_wind_calibration.csv` — özet tablo
- `tables/12_era5_hourly_wind.csv` — 1,840 saatlik raw veri
- `figures/12_era5_wind_rose.png` — histogram + polar wind rose

## Sonraki Çalışma

ERA5 hız (speed) bilgisi modelde değil. Eğer rüzgar **şiddetinin** mekânsal varyansı yüksekse (örneğin kıyı bantı vs iç kara), `effective_DTC = DTC × f(wind_speed)` türü ek bir feature düşünülebilir. Ancak ERA5 native 31 km — Konyaaltı pilot bölgesi (5×5 km) bu çözünürlükte tek piksele düşer; rüzgar şiddetinin pilot içi mekânsal varyans bilgisi yoktur. Daha yüksek çözünürlüklü mezoskala model (WRF, vb.) gerekir.
