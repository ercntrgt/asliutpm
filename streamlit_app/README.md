# UTPM Karar Destek Asistanı (Streamlit Prototipi)

Antalya Konyaaltı için kentsel ısı kalıcılık tarama aracı. Kullanıcı haritada bir 30 m grid hücresi seçer; uygulama o hücrenin UTPM skoru, sınıfı, persistence durumu ve AI yorumunu sunar.

## Önkoşullar

1. Hafta 1-13 pipeline'ı tamamlanmış olmalı (`grid_30m_utpm.gpkg`, `grid_30m_persistence.gpkg`, `grid_30m_full.gpkg` mevcut).
2. Conda `utpm` ortamı kurulu (`environment.yml` üzerinden).

## Çalıştırma

```powershell
conda activate utpm
cd streamlit_app
streamlit run app.py
```

Tarayıcı otomatik açılmazsa `http://localhost:8501` adresine gidin.

## Anthropic API key (opsiyonel)

AI yorumu için API key gerekir. Üç seçenek:

### 1. Streamlit secrets (önerilen)

`streamlit_app/.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

(Bu dosya `.gitignore`'da; commit edilmez.)

### 2. Ortam değişkeni

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
streamlit run app.py
```

### 3. Uygulama içinden

Yan paneldeki "Anthropic API key" alanına yapıştırın. Sadece o session için geçerli.

**API key yoksa:** uygulama template-based fallback yorum kullanır (kalitesiz ama çalışır).

## Modüller

- **`utils.py`** — veri yükleme (cache'li), koordinattan hücre arama, hücre özeti, komşuluk karşılaştırma
- **`claude_explainer.py`** — Claude API (system prompt + user prompt builder + fallback template)
- **`app.py`** — Streamlit ana uygulaması (folium harita + tıklama → detay paneli + AI)

## Üretilen UI

- Sol panel: harita (folium + UTPM choropleth + pilot sınır + tooltip)
- Sağ panel: seçilen hücrenin paneli — UTPM, LST, LISA, persistence, 7 değişken, AI yorumu
- Yan panel: API key, komşuluk yarıçapı, cache temizleme

## Sınırlılıklar

- Folium 28K poligon ile ağır render — ilk yüklemede 5-10 saniye.
- Hold-out R²=0.10 (Hafta 10) → uygulama UTPM'i yorumlarken **sadece pilot içi** güvenilir.
- Claude API yanıtı LLM'in mevcut bilgisine dayanır, sayısal hesaplama değil.
