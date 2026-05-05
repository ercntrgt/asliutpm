# Streamlit Cloud Deploy — UTPM Konyaaltı

Bu uygulamayı **online erişilebilir** yapmak için Streamlit Community Cloud üzerinden deploy talimatları.

## Adımlar

### 1. Streamlit Community Cloud Hesabı

1. https://share.streamlit.io adresine gidin
2. **"Sign in with GitHub"** ile giriş yapın
3. GitHub hesabınız `ercangpg` veya `ercntrgt` ile yetkilendirilecek

### 2. Yeni Uygulama Oluştur

1. Sağ üst **"New app"** butonuna tıklayın
2. **"From existing repo"** seçeneğini seçin
3. Form alanları:
   - **Repository:** `ercntrgt/asliutpm`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app/app.py`
   - **App URL** (sub-domain): istediğiniz isim, örn. `utpmkonyaalti` → URL `utpmkonyaalti.streamlit.app`

### 3. Advanced Settings (önerilen)

**Python version:** 3.11

**Secrets** (kritik — Anthropic API key için):

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-XXXXXXXXXXXXXXXX"
```

API key olmadan uygulama çalışır ama AI yorumu **kural-tabanlı fallback** kullanır (Claude API yerine template).

### 4. Deploy

**"Deploy!"** butonuna tıklayın. İlk deploy:
- Build süresi: **3-5 dakika**
- requirements.txt'den paket yükleme
- Veri dosyalarını clone'lama (~10 MB)

Başarılı olursa URL açılır → tarayıcıdan kullanılabilir.

### 5. Sonraki Güncellemeler

GitHub'a yeni commit push'larsanız uygulama **otomatik redeploy** olur. Manuel müdahale gerekmez.

## Veri Boyutu Notu

`streamlit_app/data/` altında ~10 MB veri:

| Dosya | Boyut | Amaç |
|---|---|---|
| `grid_30m_full.gpkg` | 9.4 MB | 28K hücre lookup tablosu |
| `pilot_boundary.gpkg` | 116 KB | Pilot sınır overlay |
| `utpm_choropleth.png` | 9.5 KB | UTPM 5-sınıf raster |
| `utpm_bbox.json` | 0.2 KB | Folium ImageOverlay bbox |

GitHub repo limitleri içinde. Büyük dosyalar (RF model 1.2 GB) **deploy edilmez** — uygulama önceden hesaplanmış UTPM tahminlerini okur.

## Performans

**Çözülen sorun:** 28K poligon Folium GeoJSON yavaştı (5-10 sn ilk render). Çözüm: PNG ImageOverlay (9.5 KB, instant render).

**30 m hassasiyet korunur:** kullanıcı haritaya tıklayınca → spatial query ile en yakın 30 m hücre bulunur, sağ panelde detay gösterilir.

**Streamlit Cloud free tier:**
- 1 GB RAM (kullanım ~200 MB)
- 1 vCPU
- İlk açılış 5-15 sn (cold start), sonra hızlı

## Uygulama Akışı

1. **Harita yüklenir** (1-2 sn): pilot sınır + UTPM PNG raster
2. **Kullanıcı haritaya tıklar** → koordinat alınır
3. **Spatial query** → en yakın 30 m hücre bulunur
4. **Sağ panel** → UTPM/LST/sınıf/LISA/persistence/komşuluk/7 feature
5. **AI yorumu** → Claude API'ye gönderilir (varsa) ya da fallback template

## Sınırlılıklar

- LISA katmanı opsiyonel (yan panelde toggle) — açılırsa ~12K poligon yüklenir, yavaşlatır
- AI yorumu için API key gerekli (yoksa fallback)
- Streamlit Cloud free tier kapasitesi:
  - 1 GB RAM, 1 vCPU
  - Boş kalırsa otomatik uyku, ilk istek cold start

## Yerel Test (Deploy Öncesi)

```powershell
conda activate utpm
cd streamlit_app
streamlit run app.py
```

Tarayıcı `localhost:8501`'i otomatik açar.

## Sorun Giderme

**"Module not found" hatası:** `requirements.txt`'de eksik paket. Repo root'a ekleyin, push'layın.

**Veri yüklenmiyor:** `streamlit_app/data/` klasörünün repo'da olduğunu kontrol edin (`.gitignore` istisnası).

**API key çalışmıyor:** Streamlit Cloud → app → Settings → Secrets'a gidin, TOML formatında yapıştırın.

**Cold start çok yavaş:** Free tier sınırı. Pro/Teams plana geçilmeden çare yok.

## Alternatifler

Streamlit Cloud yerine:
- **Hugging Face Spaces** (Streamlit destekli, GPU opsiyonel)
- **Render.com** (free tier, build süresi uzun)
- **Railway.app** (5$ kredisi, hızlı)
- **Fly.io** (free hobby plan, Docker)

Hepsi GitHub repo'dan auto-deploy destekler.
