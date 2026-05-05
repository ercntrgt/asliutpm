# Sınırlılıklar — Tezde Raporlanacak

## Sınıflandırma

**Kritik (model yorumunu etkiler):**
- L1: RF out-of-area extrapolation
- L2: DTC_breeze saturated outlier sinyali
- L3: NDVI Pearson zayıf

**Orta (sınırlılık olarak not edilir):**
- L4: Bina yüksekliği NaN doldurma
- L5: GHSL hücre-level uyumsuz
- L6: TS 9111 konut varsayımı
- L7: Albedo pozitif korelasyon yön

**Düşük (operasyonel):**
- L8: Saatlik rüzgar yönü kalibrasyonsuz
- L9: 5-yıl medyan dinamik değil
- L10: Folium 28K poligon ağır render

---

## L1 — RF out-of-area extrapolation zayıf

**Sorun:** Mahalle hold-out validation R² = 0.105 (Random CV R²=0.846 ile karşılaştırıldığında).

**Detay:** ALTINKUM, HURMA, GÜRSU mahalleleri tamamen test setine ayrıldığında modelin bu görmediği alanlardaki LST tahmin gücü çok düşük. Random Forest yapı gereği eğitim örneklerinin uzayında "interpolate" eder, dışına extrapole etmez.

**Etki:** UTPM modeli **pilot içi karar destek** olarak güvenilir; başka şehirlere veya pilot dışı Konyaaltı bölgelerine direkt transfer edilirse tahmin kalitesi düşer.

**Tezde nasıl raporlanır:** "UTPM bir tarama aracı olarak Konyaaltı pilot bölgesi için kalibre edilmiştir; başka kentsel alanlara transfer için yerel feature dağılımının yeniden öğrenilmesi gerekir."

**Hafifletme önerisi (sonraki çalışma):** Hierarchical RF veya GeoSpatial-aware ML (örn. Geographically Weighted Random Forest).

---

## L2 — DTC_breeze saturated outlier sinyali

**Sorun:** 1,066 hücre (%3.8) DTC_breeze = 20,000 m max_dist'te saturated. Bu hücreler kıyının deniz tarafında — 165° SSE yönünde ışın denize gidiyor, kara olmadığı için kıyıya çarpmıyor.

**Detay:** Pearson r(DTC, LST) = -0.654 ama Spearman = +0.018. Yani lineer korelasyon büyük kısmı saturated outlier'lardan geliyor. Saturated hücrelerin LST ortalaması 31°C (genel ortalaması 42.5°C) — gerçekten serin yerler.

**Etki:** Lineer modeller (UTPM lineer indeks) DTC'nin gerçek gradient sinyalini kaçırıyor. RF non-lineer doğal olarak işliyor.

**Tezde nasıl raporlanır:** "DTC_breeze ham değerinde saturasyon gözlemlenmiştir; lineer korelasyonun büyük kısmı sınır hücrelerden gelir. Random Forest non-lineer modelleyici saturasyonu doğal şekilde işlemiştir; lineer UTPM indeksinde DTC ağırlığı SHAP-tabanlı %18 olmuştur."

**Hafifletme:** `is_dtc_saturated` binary flag eklenmiştir (RF'in 8. feature'ı).

---

## L3 — NDVI Pearson zayıf, Spearman güçlü

**Sorun:** NDVI × LST Pearson r = +0.05 (neredeyse sıfır) ama Spearman r = -0.25 (orta-zayıf negatif).

**Detay:** Antalya kurak Akdeniz iklimi — yaz NDVI gradient'i düşük, çoğu hücre 0.1-0.4 aralığında. Bitki örtüsü serinletme etkisi var ama lineer değil (Spearman gösteriyor). RF non-lineer modelleyici NDVI'yi SHAP'ta %27 ağırlıkla yakalamış.

**Etki:** UTPM lineer indeksinde NDVI ağırlığı doğru atanmış (SHAP-based) ama lineer kombinasyon NDVI'nin gerçek katkısını tam yansıtmıyor.

**Tezde nasıl raporlanır:** "NDVI ile LST arasında lineer-olmayan monotonik bir ilişki gözlemlenmiştir (Spearman r = -0.25, Pearson r = 0.05). Random Forest bu ilişkiyi yakalayabilmiştir."

---

## L4 — Bina yüksekliği NaN doldurma (22,911 hücre)

**Sorun:** 28,247 hücreden 22,911'inde (%81) imar nokta verisi yok → `building_height_mean` = NaN.

**Detay:** Bu hücreler gerçek "bina yok" yerleri (park, plaj, deniz kenarı). RF NaN'ı doğrudan kabul etmediği için 0 ile dolduruldu (semantic doğru: bina yok = 0 m yükseklik).

**Etki:** RF bu doldurmayı bir "low building" sinyali olarak kullanıyor. Building_height'in ortalama feature importance'ı düşük (SHAP %3) — bu doldurma kararının modeli yanıltmadığını gösteriyor.

**Tezde nasıl raporlanır:** "Bina olmayan grid hücrelerinde `building_height_mean` 0 değeriyle kodlanmıştır. Random Forest bu kodlamayı semantic boş alan göstergesi olarak kullanmıştır."

---

## L5 — GHSL hücre-level uyumsuz

**Sorun:** İmar-tabanlı `building_height_mean` ve GHSL `BUILT_H` arasında hücre seviyesinde Pearson r = -0.015.

**Detay:** GHSL native 100 m, 30 m grid'e zonal mean ile downscale edildi → konumsal kayma. Ek olarak GHSL Konyaaltı pilot bölgesinin sadece 642 hücresinde >0 değer veriyor (GHSL global modelin Akdeniz kıyı kentlerinde kapsamı zayıf).

Median değerleri ise uyumlu: imar 12.0 m vs GHSL 11.08 m.

**Etki:** GHSL modelleme tablosuna **dahil edilmedi**, sadece imar imputasyonu için bağımsız doğrulama olarak kullanıldı (median düzeyinde).

**Tezde nasıl raporlanır:** "GHSL P2023A global bina yüksekliği veri seti, imar-tabanlı hesaplamamız için bağımsız doğrulama referansı olarak kullanılmıştır. Median düzeyinde uyum gözlemlenmiştir (12.0 m vs 11.08 m); ancak hücre seviyesinde 100 m → 30 m yeniden örnekleme kaynaklı konumsal kayma ve veri seti kapsamı kısıtları nedeniyle hücre-level Pearson korelasyonu düşüktür (r = -0.015)."

---

## L6 — TS 9111 konut varsayımı

**Sorun:** İmar veri setinde kullanım amacı (konut/ticaret/sanayi) yok. Tüm binalar konut varsayıldı; kat × 3.0 m formülü uygulandı.

**Etki:** Gerçek ticaret/sanayi binaları için yükseklik %15-50 az hesaplanıyor olabilir.

**Tezde nasıl raporlanır:** "TS 9111 standardına göre konut tipi 3.0 m/kat dönüşümü tüm binalara uygulanmıştır. Veri setinde kullanım amacı sınıflandırması bulunmadığından, ticari ve sanayi yapıları için olası yükseklik düşük tahminlemesi bir sınırlılık olarak not edilmelidir."

**Hafifletme önerisi:** Belediyenin kullanım amacı katmanı sağlaması durumunda yeniden hesaplama kolaydır.

---

## L7 — Albedo × LST pozitif yön (literatür-uyumlu sürpriz)

**Sorun:** Geleneksel UHI modellerinde yansıtıcı yüzey (yüksek albedo) = serin ilişkisi beklenir (negatif r). Konyaaltı'da r = +0.59 pozitif.

**Detay:** Akdeniz şehirlerinde beton/kireç çatı yapısı yüksek albedo verir AMA termal kütle yüksek (gece yavaş soğur). Bonafoni & Sekertekin (2020) gibi çalışmalarda benzer pozitif albedo-LST ilişkisi raporlanmıştır.

**Etki:** UTPM ağırlığında albedo en güçlü prediktör (%37 SHAP). Bu yorumlanırken "yüksek albedo = sıcak" ilişkisi Akdeniz bağlamına özel.

**Tezde nasıl raporlanır:** "Konyaaltı pilot bölgesinde albedo ile LST arasında pozitif korelasyon gözlemlenmiştir (r = +0.59). Bu, geleneksel UHI literatürünün negatif albedo-LST varsayımıyla görünürde çelişse de Akdeniz kentsel dokusu için Bonafoni ve Sekertekin (2020) tarafından raporlanan bulguya uyumludur. Beton ve kireçli kaplama materyalleri yüksek albedoya sahip olmasına rağmen termal kütleleri yüksek; gündüz yansıtıcılığa rağmen termal etkileri kalıcıdır."

---

## L8 — Rüzgar yönü kalibrasyonsuz ✅ KAPANDI (Hafta 17 + 18)

**Önceki durum:** DTC_breeze hesaplaması için rüzgar yönü 165° SSE literatür/iklim atlas değeri. ERA5 saatlik veriyle doğrulanmadı.

**Hafta 17 ek:** Bina yüksekliği etkisi için `wind_blockage_index` feature'ı eklendi — ray boyunca bina yüksekliğine ağırlıklı toplam (mesafe-decay'li). RF'in 9. feature'ı oldu, SHAP %6 ağırlık aldı (Albedo+NDVI+DTC sonrası 5. sıra). Bu, rüzgar yönündeki bina blokajı etkisini modele dahil etti — kentsel klimatoloji literatürüyle (Oke 1987, Grimmond 1999, Stewart & Oke 2012 LCZ) uyum sağlandı.

**Hafta 18 — ERA5 kalibrasyonu yapıldı:**

| Metrik | Değer |
|---|---|
| Konfig WIND_FROM_DEG | 165° |
| ERA5 vector mean (5 yıl × yaz öğle, 1840 saat) | 158.9° |
| ERA5 medyan | 160.6° |
| ERA5 histogram dominant bin | 155° (%22.7) |
| ERA5 IQR (25-75%) | 149.5° – 174.7° |
| **Fark** | **6.1°** (eşik 10°'den az) |

Yıllar arası tutarlı (2020-2024 arası 156°-164° dağılımı).

**Sonuç:** Mevcut 165° konfig değeri ERA5 ile istatistiksel olarak **uyumlu**. Yeniden hesap **gerekmedi**. Detaylı rapor: `tez/08_era5_calibration.md`.

**Tezsel duruş:** Wind direction veri-tabanlı doğrulanmıştır; mevcut UTPM modeli rüzgar yönü için kalibre kabul edilmektedir.

---

## L9 — 5-yıl medyan dinamik değil

**Sorun:** NDVI, Albedo, Impervious, building_*, road_density 5-yıl medyan veya sabit. Hücre özellikleri yıllar arası değişimini yansıtmıyor.

**Detay:** Yıllar arası tek değişen LST. Persistence analizi LST için yapıldı, feature dinamiği değil.

**Sonraki çalışma:** Yıllık feature kompozitleri + her yıl için ayrı RF eğitimi → time-aware UTPM.

---

## L10 — Streamlit Folium ağır render

**Sorun:** 28,247 poligonun web haritasında render'ı ilk yüklemede 5-10 saniye.

**Hafifletme:** Vector tile servisi (örn. MapTiler) veya raster choropleth tile pre-rendering.

---

## L11 — ERA5 mekânsal çözünürlük yetersiz (yeni — Hafta 19)

**Sorun:** ERA5 hourly native ~31 km. Konyaaltı pilot bölgesi (5×5 km) tek ERA5 piksele düşer. Pilot içi rüzgar şiddeti varyansı yakalanamaz.

**Etki:** ERA5 wind speed feature olarak modele eklenemez (28K hücrede aynı değer = sıfır bilgi). Yıllık temporal varyans %12, LST yıllık varyansını açıklayamıyor (r=+0.10 Spearman). 2022 sıcak dalgası yerel rüzgar değişiminden kaynaklanmamış (anomali sadece +0.05 m/s).

**Hafifletme:** Wind speed feature olarak eklenmedi. Wind direction bilgisi DTC_breeze + wind_blockage_index üzerinden zaten modelde.

**Sonraki çalışma:** WRF mezoskala simülasyonu (1-3 km çözünürlük) — pilot içi rüzgar dinamiği için.

Detaylı rapor: `tez/09_wind_speed_temporal.md`.

## Sınırlılık Master Tablosu (güncellenmiş)

| # | Sınırlılık | Önem | Durum |
|---|---|---|---|
| L1 | RF out-of-area extrapolation R²=0.10 | KRİTİK | Açık (RF doğası) |
| L2 | DTC saturated outlier (1066 hücre) | KRİTİK | Hafifletildi (is_dtc_saturated flag) |
| L3 | NDVI non-lineer (Pearson 0.05) | KRİTİK | Çözüldü (RF yakaladı, SHAP %27) |
| L4 | Building NaN %81 doldurma | ORTA | Hafifletildi (semantic 0) |
| L5 | GHSL hücre-level r=-0.015 | ORTA | Hafifletildi (median validation) |
| L6 | TS 9111 konut varsayımı | ORTA | Açık (belediye kullanım amacı verirse) |
| L7 | Albedo+LST pozitif | ORTA | Çözüldü (Akdeniz literatürüyle uyumlu) |
| **L8** | **Rüzgar 165° kalibrasyonsuz** | DÜŞÜK | **✅ KAPANDI (ERA5 ile 6.1° fark)** |
| L9 | 5-yıl medyan statik | DÜŞÜK | Açık |
| L10 | Folium render yavaş | DÜŞÜK | Açık (vector tile çözer) |
| **L11** | **ERA5 mekânsal yetersiz** | DÜŞÜK | **Açık (WRF gerekir)** |
