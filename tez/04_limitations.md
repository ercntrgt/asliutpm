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

## L8 — Rüzgar yönü kalibrasyonsuz (kısmen düzeltildi — Hafta 17)

**Sorun:** DTC_breeze hesaplaması için rüzgar yönü 165° SSE literatür/iklim atlas değeri. ERA5 saatlik veriyle doğrulanmadı.

**Etki:** Yön sapması gerçek meltemden ±15° farklıysa DTC_breeze değerleri anlamlı şekilde değişebilir.

**Hafta 17 ek:** Bina yüksekliği etkisi için `wind_blockage_index` feature'ı eklendi — ray boyunca bina yüksekliğine ağırlıklı toplam (mesafe-decay'li). RF'in 9. feature'ı oldu, SHAP %6 ağırlık aldı (Albedo+NDVI+DTC sonrası 5. sıra). Bu, rüzgar yönündeki bina blokajı etkisini modele dahil etti — kentsel klimatoloji literatürüyle (Oke 1987, Grimmond 1999, Stewart & Oke 2012 LCZ) uyum sağlandı.

**Hala kalan sorun:** Rüzgar **yönü** ERA5 ile kalibre edilmedi. Sadece bina blokajı eklendi (yön sabit 165°).

**Sonraki çalışma:** ERA5 reanalysis 2020-2024 yaz öğle saatleri rüzgar yönü dağılımı çek, dominant yönü kalibre et, blockage_index'i o yönde yeniden hesapla.

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

## Sınırlılık Master Tablosu

| # | Sınırlılık | Önem | Hafifletme/Sonraki çalışma |
|---|---|---|---|
| L1 | RF out-of-area extrapolation R²=0.10 | KRİTİK | GeoRF, hierarchical model |
| L2 | DTC saturated outlier (1066 hücre) | KRİTİK | is_dtc_saturated flag eklendi |
| L3 | NDVI non-lineer (Pearson 0.05) | KRİTİK | RF doğal olarak yakaladı |
| L4 | Building NaN %81 doldurma | ORTA | semantic 0 doğru, RF kullanıyor |
| L5 | GHSL hücre-level r=-0.015 | ORTA | sadece median validation kullanıldı |
| L6 | TS 9111 konut varsayımı | ORTA | belediye kullanım amacı verirse düzelir |
| L7 | Albedo+LST pozitif | ORTA | Akdeniz literatürüyle uyumlu |
| L8 | Rüzgar 165° kalibrasyonsuz | DÜŞÜK | ERA5 ile yeniden hesap |
| L9 | 5-yıl medyan statik | DÜŞÜK | yıllık feature kompoziti |
| L10 | Folium render yavaş | DÜŞÜK | vector tile |
