# Şehir Planlamacısına Öneri Belgesi

## Özet

UTPM Konyaaltı pilot bölgesinde **5 yıllık (2020-2024) tutarlı kentsel ısı kalıcılığı** desenleri ortaya koymuştur. Şehir planlamacılarına dönük 3 katmanlı eylem önceliği önerilmektedir.

---

## Eylem Önceliği

### 🔴 ÖNCELİK 1 — Çok Sıcak Hücreler (Acil Müdahale)

**881 grid hücresi (0.79 km², pilotun %3.1'i)** UTPM Jenks "Çok sıcak" sınıfında.

**Tipik özellikleri:**
- LST 5-yıl medyan: > 45 °C
- Yüksek albedo + yüksek geçirimsiz yüzey + kara içi (DTC > 2000 m)
- Genelde alçak bina + asfalt kaplı alan

**Mahalle dağılımı:** Operasyonel olarak HURMA, ULUÇ, MOLLA YUSUF, TOROS'un iç kara taraflarında yoğunlaşma bekleniyor (uydu görselleri ile teyit edilmeli).

**Öneriler:**
1. **Soğuk çatı boyası** — beton/kireç çatılarda termal yansıtıcı kaplama
2. **Sokak ağacı dikilimi** — gölge etkisi LST'yi 2-5 °C düşürür
3. **Geçirimsiz yüzey azaltma** — otopark üzerlerinde geçirgen kaplama
4. **Bisiklet/yaya bandı dönüşümü** — asfalt yüzey yerine yeşil bant

### 🟠 ÖNCELİK 2 — LISA HH Cluster (UHI Çekirdekleri)

**5,181 grid hücresi (4.66 km², pilotun %18.3'ü)** istatistiksel olarak anlamlı sıcak küme (HH = High-High, p < 0.05).

**Anlam:** Sadece bireysel olarak değil, **çevreleriyle birlikte** sıcak. Müdahale "tek hücre" yerine "bölge ölçeğinde" planlanmalı.

**Öneriler:**
1. **Mahalle ölçekli yeşil koridor** — HH cluster içinden geçen bağlantılı yeşillendirme
2. **Su elementleri** — fıskiye, gölet, ıslak yüzeyler
3. **Bina yenileme programı** — sayrılaşma + termal yalıtım
4. **Otobüs durağı + kamu alanı** soğuk noktalandırma

### 🟢 ÖNCELİK 3 — LL Cluster (Serin Adalar Koruma)

**5,860 grid hücresi (5.27 km², pilotun %20.7'si)** istatistiksel olarak anlamlı serin küme.

**Tipik özellikleri:**
- Kıyıya yakın (DTC saturated bölgeler dahil)
- Yeşil alan, park, plaj, tarım

**Öneriler:**
1. **Koruyucu zonlama** — bu cluster'larda yapılaşma kısıtı
2. **Yeşil alan envanteri** — mevcut korunan alanlar haritalansın
3. **Bağlantılı yeşil ağ** — LL cluster'larını ana caddelerle bağlayan koridor planlaması

---

## Persistent Hot Spots Listesi (5/5 yıl Q4)

**2,008 grid hücresi** 2020-2024 boyunca her yıl en sıcak quartile'da kaldı. Bu hücreler **kalıcı UHI çekirdeği** olarak öncelikli izleme altına alınmalı.

**İzleme metrikleri:**
- Yıllık LST std (yıllar arası varyans)
- Yıllık LST mean (genel ısınma trendi)
- Yıllık Q4 yıl sayısı (bu sayı düşmediyse müdahale etkisiz)

---

## Müdahale Etkinliği İzleme

UTPM 0-100 indeksi yıllık olarak yeniden hesaplanabilir. Önerilen etkinlik metriği:

```
Etkinlik = ΔUTPM_score / yıl
```

Hedef: müdahale yapılan hücrelerde ΔUTPM_score < -2 puan/yıl (ısınma azalması).

---

## Karar Destek Aracı Kullanımı

### QGIS ile

1. `data/processed/grid_30m_utpm.gpkg` dosyasını aç
2. Symbology → Categorized → kolon `utpm_class`
3. Renk şeması: 0=#264653 (Çok serin), 1=#2A9D8F, 2=#E9C46A, 3=#F4A261, 4=#E76F51 (Çok sıcak)
4. LISA için aynı dosyada `lisa_cluster` kolonu (HH/LL/HL/LH/NS)

### Streamlit web uygulaması ile

```
conda activate utpm
cd streamlit_app
streamlit run app.py
```

Tarayıcıda `localhost:8501` → tıkla → o noktanın UTPM skoru, sınıfı, persistence, AI yorumu.

---

## Öneri Önceliklendirme Tablosu

| Hücre durumu | Sınıf | Mevcut planlama yaklaşımı | UTPM Önerisi |
|---|---|---|---|
| Persistent HOT (5/5 Q4) + LISA HH | Çok sıcak | Genel ısınma | **Acil bölgesel müdahale** |
| Persistent HOT + LISA NS | Çok sıcak/Sıcak | Tek bina müdahalesi | Hücre-bazlı çatı/yol düzenleme |
| LISA HH + persistent değil | Sıcak | Konvansiyonel UHI | Yeşillendirme önceliği |
| LISA LL (serin küme) | Çok serin/Serin | Genel zonlama | **Koruma + yeşil koridor bağlantı** |
| Yerel anomali HL | Çok sıcak ama serin komşu | Belirsiz | **Detay analiz** (yapı tipi/yaş kontrol) |

---

## Sınırlılıklar — planlamacı için kısa not

- UTPM **pilot içi** karar destek aracıdır. Konyaaltı dışındaki bölgelere transfer önerilmez (RF hold-out R²=0.10).
- Müdahale etkilerinin somutlanması için en az 2-3 yaz geçmesi gerekir (LST 5-yıl medyan stabil).
- Bina yüksekliği imar verisinden (TS 9111 konut varsayımı) — ticaret/sanayi yapıları için yeniden hesaplama gerekebilir.
- AI yorumu (Streamlit) bilgilendirme amaçlı; karar mercii planlamacı.
