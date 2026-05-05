# Hafta 20 — Bivariate Karar Destek Katmanı: UTPM × Wind Blockage

## Motivasyon

UTPM 0-100 sürekli skoru ve Jenks 5-sınıf ısıl yorumu sundu (Hafta 13). Wind blockage index ise rüzgar yönündeki yapısal engellemeyi ölçtü (Hafta 17). Bu iki katman **bağımsız bilgi** taşıyor (r=-0.004) — birleştirildiğinde **eylem-yönelimli kategoriler** ortaya çıkar.

**Hipotez:** Şehir planlamacısı için "**sıcak + bloklu**" hücreler "**sıcak + açık**" hücrelerden farklı müdahale gerektirir:
- **Sıcak + Bloklu:** binalar arasındaki ısı tutuluyor, rüzgar erişimi yok → çatı/sokak ağaçlandırma + bina arası açıklık
- **Sıcak + Açık:** kıyıya yakın ama termal kütle (asfalt/beton) → soğuk çatı + yansıtıcı yüzey
- **Serin + Bloklu:** muhtemelen gölgeli iç bahçe / sokak vadisi → koruma
- **Serin + Açık:** kıyı/park/yeşil → yeşil koridor koruma

## Yöntem

1. **Tertile sınıflama** — UTPM ve Wind Blockage hücreleri 3'erli sınıfa ayır (alt %33 / orta %33 / üst %33).
2. **3×3 bivariate matrix** — 9 kombinasyon → her hücreye `bivariate_class` (0-8).
3. **Önceliklendirme etiketi** (`priority_label`):

| UTPM tier | Blockage tier | Etiket | Eylem |
|---|---|---|---|
| 2 (yüksek) | 2 (yüksek) | **1_ACİL_MÜDAHALE** | Çatı + bloklar arası açma |
| 2 (yüksek) | 1 (orta) | 2_YÜKSEK_ÖNCELİK | Çatı + sokak ağacı |
| 2 (yüksek) | 0 (düşük) | 3_SICAK_AÇIK | Soğuk çatı + yansıtıcı |
| 1 (orta) | 2 (yüksek) | 4_BLOKLU_ORTA | Bina aralık planlaması |
| 1 (orta) | 1 (orta) | 5_ORTA | İzleme |
| 1 (orta) | 0 (düşük) | 6_ORTA_AÇIK | Düşük öncelik müdahale |
| 0 (düşük) | 2 (yüksek) | 7_BLOKLU_SERİN | Gölge koruma |
| 0 (düşük) | 1 (orta) | 8_SERİN_ORTA | İzleme |
| 0 (düşük) | 0 (düşük) | **9_KORUMA** | Yeşil koridor koruma |

## Tertile Eşikleri

| | UTPM | Wind Blockage |
|---|---|---|
| Alt-orta sınır | 32.1 | 0.000 (medyan üst sıfır!) |
| Orta-üst sınır | 42.7 | 0.230 |

**Not:** Wind blockage alt tertile'ı 0.000 — yani **hücrelerin %33'ünde rüzgar yönünde hiç bina yok** (kıyıya yakın açık alanlar). Bu Konyaaltı'nın kıyı şeridi karakterini yansıtıyor.

## Sonuçlar

### Hücre dağılımı

| Öncelik | Hücre | Alan (km²) | UTPM medyan | Blockage medyan | LST medyan |
|---|---|---|---|---|---|
| **🔴 1_ACİL_MÜDAHALE** | **4,420** | **3.98** | 48.1 | 0.42 | **43.5°C** |
| 🟠 2_YÜKSEK_ÖNCELİK | 1,675 | 1.51 | 47.2 | 0.14 | 43.7°C |
| 🟧 3_SICAK_AÇIK | 3,321 | 2.99 | 48.5 | 0.00 | **44.3°C** |
| 🟫 4_BLOKLU_ORTA | 3,039 | 2.74 | 38.8 | 0.34 | 43.2°C |
| 🟡 5_ORTA | 1,990 | 1.79 | 38.2 | 0.12 | 43.4°C |
| 🟨 6_ORTA_AÇIK | 4,386 | 3.95 | 37.2 | 0.00 | 43.4°C |
| 🟢 7_BLOKLU_SERİN | 1,813 | 1.63 | 24.0 | 0.36 | 42.1°C |
| 🟩 8_SERİN_ORTA | 1,468 | 1.32 | 24.1 | 0.12 | 42.2°C |
| 💚 9_KORUMA | **6,135** | **5.52** | 23.3 | 0.00 | 41.6°C |

**Toplam:** 28,247 hücre / 25.42 km² (pilot bütünü).

### Tezsel yorum

1. **3,321 hücre "Sıcak + Açık" (LST 44.3°C en yüksek!)** — kıyıya yakın ama yapısal blokaj olmamasına rağmen **en sıcak medyana sahip**. Bu hücreler büyük olasılıkla **kıyıdaki turist tesisleri, otopark alanları, açık asfalt yüzeyler**. Müdahale: **albedo manipülasyonu** (soğuk çatı, yansıtıcı kaplama) — rüzgar zaten ulaşıyor.

2. **4,420 hücre "Acil Müdahale"** (3.98 km², %16) — **hem sıcak hem bloklu** = klasik UHI çekirdeği. Bina yenileme + sokak ağaçlandırma + bloklar arası mikro-park.

3. **6,135 hücre "Koruma"** (5.52 km², %22) — pilotun en büyük tek kategori. Bunlar Konyaaltı'nın **mevcut serin alanları** (plaj, park, yeşil koridor). Yapılaşma kısıtı + koruyucu zonlama.

4. **3_SICAK_AÇIK > 1_ACİL_MÜDAHALE LST medyanı** — açık alandakiler bloklu sıcak hücrelerden ~0.8°C daha sıcak. **Beklenmedik ama mantıklı**: bloklu alanlarda gölge etkisi LST'yi hafif düşürüyor (binalar arası gölge), açık asfalt direkt güneş alıyor.

## Streamlit Entegrasyonu

`streamlit_app/app.py` artık seçilen hücre için `priority_label` gösteriyor + `wind_blockage_index` değeri + tier bilgisi (UTPM/Blockage 0-2 ölçek).

`streamlit_app/claude_explainer.py` system prompt'una priority bilgisi eklendi → AI yorumu eylem önerirken bu sınıfı kullanır:
- "1_ACİL_MÜDAHALE" → çatı+bloklar arası açma vurgusu
- "3_SICAK_AÇIK" → soğuk çatı vurgusu
- "9_KORUMA" → yeşil koridor koruma vurgusu

## Karar Destek Açısı

Şehir planlamacısı için bu katman **eylem-yönelimli**:

```
ÖNCE → 1_ACİL_MÜDAHALE (4,420 hücre)
    ↓
SONRA → 2_YÜKSEK_ÖNCELİK + 3_SICAK_AÇIK (4,996 hücre)
    ↓
İZLEME → 4_BLOKLU_ORTA + 5_ORTA + 6_ORTA_AÇIK (9,415 hücre)
    ↓
KORUMA → 7,8,9 (9,416 hücre)
```

**Toplam müdahale önceliği:** 4,420 + 1,675 + 3,321 = **9,416 hücre** (8.48 km², pilotun %33.4'ü).

## Üretilen Dosyalar

- `data/processed/grid_30m_priority.gpkg` (7.5 MB) — bivariate kolonlar + priority_label
- `figures/14_bivariate_decision.png` — bivariate harita + priority harita + 3×3 legend matrix
- `tables/14_priority_summary.csv` — 9 öncelik özet tablo
- `results/bivariate_decision.json` — JSON özet

## Sınırlılıklar

- Tertile sınırları **bu pilot bölgeye özel** — başka şehre transfer için lokal yeniden hesap
- 3×3 = 9 sınıf belki **çok ince** — 2×2 = 4 sınıf alternatif daha basit (sadece "müdahale" / "koruma" ayrımı)
- "Bloklu" kategorisi rüzgar yönü 165° SSE varsayımıyla — başka rüzgar yönlerinde sonuç farklı olur

## Sonraki Çalışma

- Mahalle bazlı önceliklendirme heatmap (her mahalle hangi kategorilerden ne kadar?)
- 100 m planlama grid'ine agregasyon (mahalle başına özet)
- Müdahale maliyet/etki simülasyonu
