# UTPM Konyaaltı — Yönetici Özeti

## Problem

Antalya Konyaaltı'nın 25.4 km²'lik kentleşmiş sahil koridorunda kentsel ısı adası (UHI) etkisi nerelerde kalıcı? Şehir planlamacılarının müdahale önceliklerini belirleyebileceği veri-tabanlı bir karar destek aracı geliştirilmesi.

## Yaklaşım

**UTPM (Urban Thermal Persistence Model):** 30 m grid çözünürlüğünde Landsat yer yüzey sıcaklığını (LST) 7 mekânsal-morfolojik değişkenden Random Forest ile öğrenip, lineer bir kentsel ısı kalıcılık indeksi (0-100) üreten ve mekânsal otokorelasyonla doğrulayan model.

**Çalışma alanı:** 15 mahalle (UNCALI, ULUÇ, HURMA, MOLLA YUSUF, ÖĞRETMENEVLERİ, TOROS, SİTELER, LİMAN, GÜRSU, ARAPSUYU, KUŞKAVAĞI, PINARBAŞI, AKKUYU, ALTINKUM, SARISU).

**Veri seti:** 28,247 grid hücresi × 8 değişken (7 bağımsız + LST hedef).

## Bağımsız değişkenler

| # | Değişken | Kaynak | Doğal çözünürlük |
|---|---|---|---|
| 1 | NDVI | Sentinel-2 SR Harmonized 2020-2024 yaz medyan | 10 m |
| 2 | Albedo (Liang 2001) | Sentinel-2 | 10 m |
| 3 | Geçirimsiz yüzey oranı | ESA WorldCover v200 (2021) | 10 m |
| 4 | Bina yüksekliği ortalaması | İmar verisi + buffer cascade imputation | 30 m |
| 5 | Yapı yoğunluğu | İmar nokta sayımı / hücre alanı | 30 m |
| 6 | Yol yoğunluğu | OSM drive yolları / hücre alanı | 30 m |
| 7 | DTC_breeze | OSM coastline + ray casting (165° SSE) | 30 m |

**Hedef:** Landsat 8/9 Collection 2 Level-2, 2020-2024 yaz medyan LST (Haziran-Ağustos, bulut < %10).

## Ana bulgular

### 1. Model performansı

- **Random 5-fold CV:** R² = **0.846** (RMSE 1.22 °C)
- **Spatial Block CV (500m):** R² = 0.720 (mekânsal autocorrelation gap 0.13)
- **Mahalle hold-out (3 mahalle):** R² = **0.105** (out-of-area extrapolation zayıf)
- **Permutation null test:** p < 0.01 (model anlamlı)

### 2. SHAP feature attribution

| Özellik | SHAP ağırlığı | Yorum |
|---|---|---|
| **Albedo** | **37%** | Akdeniz beton/kireç çatı bulgusu (literatürle uyumlu) |
| **NDVI** | **27%** | Pearson 0.05 ama Spearman -0.25 → non-lineer ilişki, RF yakaladı |
| DTC_breeze | 18% | Kıyıdan rüzgar yönelimli mesafe |
| Geçirimsiz yüzey | 10% | |
| Yol yoğunluğu | 4% | |
| Bina yüksekliği | 3% | |
| Yapı yoğunluğu | 1% | Pratikte sıfır-ağırlıklı (atılabilir) |

### 3. Mekânsal otokorelasyon

- **Global Moran's I = 0.738** (z = 249.4, p < 0.001)
- **LISA HH (UHI çekirdeği): 5,181 hücre** — şehir planlamasının ilk müdahale alanı
- **LISA LL (serin küme): 5,860 hücre** — kıyı + park + tarım

### 4. Yıllar arası kalıcılık

- 5 yıl × yıllık LST kompoziti karşılaştırıldı (2020-2024 yaz)
- **Yıllar arası mekânsal LST korelasyonu mean = 0.905** (min 0.797, max 0.983)
- **Persistent HOT spots: 2,008 hücre** (5/5 yıl en sıcak quartile'da kaldı)
- **Persistent COLD spots: 3,390 hücre**

### 5. Karar destek katmanı (Jenks 5 sınıf)

| Sınıf | UTPM aralığı | Hücre | % |
|---|---|---|---|
| Çok serin | 0-21 | 4,049 | %14.3 |
| Serin | 21-34 | 6,888 | %24.4 |
| Orta | 34-44 | 9,641 | %34.1 |
| Sıcak | 44-59 | 6,788 | %24.0 |
| **Çok sıcak** | **59-100** | **881** | **%3.1** |

**881 "Çok sıcak" hücre = 0.79 km² — pilotun %3.1'i şehir planlamacısının acil müdahale önceliği.**

## Üretilen ürünler

- **Bilimsel:** 13 git commit, 11 Jupyter notebook, 11 Python modülü, 16 görsel, 10 özet tablo
- **Karar destek:** `data/processed/grid_30m_utpm.gpkg` — şehir planlamacısı QGIS'te direkt kullanabilir
- **Prototip:** Streamlit web uygulaması (folium harita + Claude API yorumu)

## Tezsel katkı

1. **Yöntem birleşimi:** Yer-tabanlı imar verisi + uydu uzaktan algılama + OSM geometrik analiz + RF ML + SHAP açıklanabilirlik + LISA mekânsal istatistik — bu 6 katmanlı entegrasyon Antalya kentsel termal araştırmalarında ilk.
2. **Bulgu:** Konyaaltı kıyı şeridinde **kalıcı UHI çekirdekleri var** ve mevcut konum bağımsız ısınmıyor — fiziksel öngörülebilir mekânsal yapıda.
3. **Pratik araç:** UTPM 0-100 indeksi belediyeye iletildiğinde mahalle/sokak düzeyinde önceliklendirme sağlar.

## Sınırlılıklar (kısa)

1. RF modelin out-of-area genelleme gücü zayıf (R²=0.10) — başka şehre direkt transfer önerilmez.
2. NDVI ve Albedo 5-yıl medyan; yıllar arası dinamiği yansıtmıyor.
3. TS 9111 dönüşümü tüm binaları konut varsaydı (3.0 m/kat).
4. DTC_breeze 165° SSE rüzgar yönü literatür değeri; ERA5 ile saatlik kalibrasyon yapılmadı.
5. GHSL bina yüksekliği global model, hücre seviyesinde Konyaaltı imar verisiyle uyumsuz (r=-0.015) — sadece yapı medyanı doğrulaması için kullanıldı.
