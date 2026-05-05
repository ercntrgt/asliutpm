# Hafta 19 — ERA5 Wind Speed Temporal Analizi

## Hipotez

**H1:** Düşük rüzgar şiddetli yıllarda kentsel ısı adası (UHI) yoğunluğu artar — durağan hava ısı birikimine ve serinletici meltem etkisinin azalmasına yol açar. Beklenen: yıllık LST ortalaması × yıllık wind speed ortalaması arasında **negatif korelasyon**.

## Yöntem

**Veri kaynağı:** ECMWF/ERA5/HOURLY (Hafta 18'de indirilen 1840 saat).

**Yıllık ortalamalar:**

| Yıl | Wind speed mean (m/s) | Wind speed median (m/s) | Wind dir mean (°) | n (saat) |
|---|---|---|---|---|
| 2020 | 2.80 | 3.01 | 154 | 368 |
| 2021 | **2.52** ← en düşük | 2.82 | 146 | 368 |
| 2022 | 2.79 | 2.92 | 161 | 368 |
| 2023 | 2.81 | 3.07 | 161 | 368 |
| 2024 | **2.83** ← en yüksek | 2.99 | 156 | 368 |

**Pilot LST yıllık ortalama:**

| Yıl | LST pilot mean (°C) |
|---|---|
| 2020 | 40.78 |
| 2021 | 41.73 |
| **2022** | **44.69** ← en yüksek |
| 2023 | 42.60 |
| 2024 | 42.39 |

## Sonuçlar

### Korelasyon (n=5)

| İstatistik | r |
|---|---|
| Pearson | +0.235 |
| Spearman | +0.100 |

**Hipotez doğrulanmadı.** Rüzgar şiddeti × LST arasında **anlamlı negatif ilişki bulunamadı**. Tam tersine, korelasyon yönü pozitif (zayıf).

### Yıllık varyans

- Wind speed: 2.52-2.83 m/s arası, sadece **%12 varyans**
- LST: 40.78-44.69 °C arası, **%9 varyans** (3.91°C aralık)

Wind speed yıllar arası **neredeyse sabit**. LST'deki anlamlı yıllar arası varyansı (özellikle 2022 +2.81°C anomali) yerel rüzgar şiddeti **açıklamıyor**.

### 2022 ekstrem yıl analizi

| Metrik | 2022 | Diğer 4 yıl ortalama | 2022 sapma |
|---|---|---|---|
| LST | 44.69 °C | 41.88 °C | **+2.81 °C** |
| Wind speed | 2.79 m/s | 2.74 m/s | +0.05 m/s |
| Wind direction | 161° | 154° | +7° |

2022 yılında:
- LST ortalama 2.81°C **yüksek**
- Wind speed pratikte **aynı** (+0.05 m/s, %1.8 fark)
- Wind direction +7° SSE → ESE'ye kaymış (Antalya hâlâ kıyı meltemi etki alanında)

**Yorum:** 2022 sıcak dalgasının kaynağı **lokal rüzgar değişimi değil**. Olası açıklamalar:

1. **Sinop ölçek sirkülasyon** — 2022 yaz Avrupa-genelinde sıcak yıl (record-breaking heatwaves)
2. **Bulut örtüsü azalması** — daha çok güneş ışınımı
3. **Atmosfer durağanlığı (anticyclone bloklama)** — pilot içi rüzgar normal görünse de yüksek atmosfer durağan
4. **Sinop yağış azlığı** — kuru toprak, düşük gizli ısı akısı

ERA5 hourly tek piksel çözünürlüğü (~31 km) bu ayrımları yapamaz; **mezoskala model (WRF) veya yüksek çözünürlüklü reanalysis** gerekir.

## Tezsel Yorum

**ERA5 wind speed Konyaaltı UTPM modeli için bağımsız bir feature olarak değerli değil:**

1. **Mekânsal:** Pilot 5×5 km tek ERA5 piksele düşer → tüm hücrelerde aynı değer → RF için sıfır bilgi
2. **Temporal:** Yıllık varyans %12, LST varyansını açıklayamıyor (r=+0.10 Spearman)
3. **2022 sıcak dalgası:** Yerel rüzgar değişiminden değil, daha geniş ölçek faktörlerden

Bu sınırlılık ERA5 native çözünürlüğünden kaynaklanır. Pilot içi rüzgar dağılımını yakalamak için **WRF mezoskala simülasyonu** (1-3 km çözünürlük) veya **özel ölçüm ağı** gerekir.

## Wind Speed Modelde Olmayacak

UTPM RF modeline `wind_speed` feature olarak eklenmesi **anlamsız** çünkü:
- 28K hücre × aynı değer = sıfır mekânsal varyans
- RF için "bilgi içermeyen" feature

UTPM zaten **rüzgar yönelimli** kıyı mesafesi (DTC_breeze) ve bina blokajı (wind_blockage_index) ile yönlendirilmiş — yön bilgisi modelde, şiddet bilgisi temporal bağlamda kalsın.

## Ek Bulgu — Yıllık Wind Direction Stabilitesi

Hafta 18'de yıllık yön ortalamaları 156°-164° aralığında idi. Bu Hafta 19 hız analiziyle birlikte değerlendirildiğinde:

- **Hem yön hem şiddet yıllar arası istikrarlı** → Konyaaltı yaz meltemi karakteri tutarlı
- LST'deki yıllar arası varyans **yerel meteorolojik faktörlerden değil** geniş ölçek + radyatif yükten kaynaklanıyor

Bu, UTPM modelinin **yapısal varyansı** (mekânsal hücreler arası) yakalamada güçlü olmasının yanında, **temporal anomalileri yerel feature'larla açıklayamadığını** gösteriyor — sınırlılık olarak raporlanır.

## Üretilen Dosyalar

- `results/wind_speed_temporal.json` — yıllık + 2022 anomali analizi
- `tables/13_lst_wind_yearly.csv` — yıllık özet
- `figures/13_lst_wind_temporal.png` — çift y-axis trend + scatter

## Sınırlılık (yeni — L11)

**L11: ERA5 hourly mekânsal çözünürlük yetersiz.** Pilot 5×5 km tek piksel ERA5'e düşer. Pilot içi rüzgar şiddeti varyansı yakalanamaz. Yüksek çözünürlüklü mezoskala model (WRF ~1 km) bu sınırlılığı kaldırabilir.

## Sonraki Çalışma

1. **WRF simülasyonu** — Konyaaltı için 1-3 km çözünürlük, lokal akım dinamiği
2. **MODIS bulut örtüsü** — yıllar arası bulutluluk × LST ilişkisi
3. **NCEP/NCAR Reanalysis 2** — sinop ölçek atmosfer durağanlığı (geopotential height, anticyclone bloklama)
4. **Yer ölçüm ağı** — Konyaaltı'da 5-10 noktalı meteorolojik istasyon dağılımı
