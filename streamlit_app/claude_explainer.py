"""Claude API yorumlama modülü — fallback template ile."""
from __future__ import annotations

import os
from typing import Optional


SYSTEM_PROMPT = """Sen Antalya Konyaaltı için geliştirilmiş UTPM (Urban Thermal Persistence Model)
kararı destek asistanısın. Kullanıcı haritada bir 30 m grid hücresi seçer; sen o hücrenin
LST/UTPM/persistence/komşuluk verisini analiz edip Türkçe, sade, planlamacı dilinde 4-6 cümlelik
bir yorum yazarsın.

ÇERÇEVE — KRİTİK: Bu model klasik **Urban Heat Island (UHI = kentsel-kırsal ΔT)** değildir.
Çalışma kırsal referansla karşılaştırma yapmaz; pilot alan içinde **yıllar arası ısı kalıcılığı**
(thermal persistence / heat retention) ölçer. Yani odak: hangi hücreler 5 yaz boyunca tutarlı sıcak
kalıyor, gece/sabah serinlemeye direniyor, ısıyı tutuyor. Bu nedenle **'kentsel ısı adası',
'UHI çekirdeği', 'ısı adası riski'** gibi ifadeleri ASLA kullanma. Bunun yerine:
'kalıcı sıcak alan', 'ısı kalıcılığı yüksek', 'gece/sabah serinlemiyor', 'soğumaya direnç',
'ısıyı tutan bölge', 'yıllar boyu sıcak kalan hücre' gibi ifadeler kullan.

Yorumun şu yapıyı izlesin:
1. Bu hücrenin termal durumunu **bir cümle** ile özetle (sıcak/orta/serin + UTPM sınıfı,
   kalıcılık vurgusu).
2. Hangi 1-2 fiziksel **etken** (albedo, NDVI, kıyı mesafesi, geçirimsiz yüzey, bina yoğunluğu)
   bu durumdan sorumlu? Veriden destekli yorum yap.
3. **Persistence** ne diyor? 5 yıl içinde kaç yıl en sıcak quartile'da olduğu önemli — 5/5 ise
   "kalıcı sıcak hücre — yıllar boyu soğumaya direnen alan".
4. **LISA cluster** durumunu yorumla (HH = kalıcı sıcak küme, LL = serin küme, NS = anlamsız).
5. **Komşu karşılaştırma**: hücre çevresine göre nasıl?
6. **Müdahale önerisi**: 1 cümle (yeşillendirme, soğuk çatı, gölge ağaç, vb.)

Klişe ifadelerden kaçın. Sayıları kullan. Doğrudan gerçeği aktar."""


def build_user_prompt(summary: dict, comparison: dict) -> str:
    """Hücre verisinden Claude'a gönderilecek user mesajını üretir. Defensive — eksik keylerde crash etmez."""
    feats = summary.get("features", {}) or {}
    pers = summary.get("persistence", {}) or {}

    lines = [
        f"30 m grid hücresi: `{summary.get('cell_id', '?')}`",
    ]
    if "mahalle" in summary and summary.get("mahalle"):
        lines.append(f"Mahalle: {summary['mahalle']}")

    lst_mean = summary.get("lst_mean")
    utpm_score = summary.get("utpm_score")
    utpm_class = summary.get("utpm_class", -1)
    utpm_label = summary.get("utpm_class_label", "?")
    lisa_cluster = summary.get("lisa_cluster", "NS")
    lisa_desc = summary.get("lisa_description", "")
    local_I = summary.get("local_I")
    lisa_p = summary.get("lisa_p")

    lines += ["", "## Termal durum"]
    if lst_mean is not None:
        lines.append(f"- LST (5-yıl medyan): **{lst_mean:.2f} °C**")
    if utpm_score is not None:
        lines.append(f"- UTPM skoru (0-100): **{utpm_score:.1f}**")
    if utpm_class is not None and utpm_class >= 0:
        lines.append(f"- UTPM sınıfı: **{utpm_label}** (Jenks {int(utpm_class) + 1}/5)")
    lines.append(f"- LISA cluster: **{lisa_cluster}** — {lisa_desc}")
    if local_I is not None and lisa_p is not None:
        lines.append(f"- Local Moran I: {local_I:.3f} (p={lisa_p:.3f})")
    lines.append("")
    lines.append("## Fiziksel özellikler")
    if feats:
        for k, v in feats.items():
            if v is not None:
                lines.append(f"- {k}: {v:.3f}")

    if pers:
        lines += ["", "## 5-yıl persistence"]
        ym = pers.get("yearly_mean_lst")
        ys = pers.get("yearly_std_lst")
        if ym is not None:
            lines.append(f"- Yıllık ortalama LST: {ym:.2f} °C")
        if ys is not None:
            lines.append(f"- Yıllar arası std: {ys:.2f} °C")
        lines.append(f"- 5 yılda en sıcak quartile'da olduğu yıl sayısı: **{pers.get('years_in_top_quartile', 0)}/5**")
        lines.append(f"- 5 yılda en serin quartile'da olduğu yıl sayısı: {pers.get('years_in_bottom_quartile', 0)}/5")

    if summary.get("priority"):
        pr = summary["priority"]
        label = pr.get("label", "?")
        nice = label.split("_", 1)[-1].replace("_", " ").title() if "_" in label else label
        lines += ["", "## Karar Önceliği"]
        if pr.get("utpm_tier") is not None and pr.get("block_tier") is not None:
            lines.append(f"- Sınıf: **{nice}** (UTPM tier {pr['utpm_tier']}/2, Blockage tier {pr['block_tier']}/2)")
        else:
            lines.append(f"- Sınıf: **{nice}**")
        wbi = pr.get("wind_blockage_index")
        if wbi is not None:
            lines.append(f"- Wind blockage index: {wbi:.3f}")

    if comparison:
        lines += [
            "",
            f"## Komşuluk ({comparison['radius_m']:.0f} m yarıçap, {comparison['n_neighbors']} hücre)",
            f"- Hedef hücre UTPM: {comparison['target_utpm']:.1f}",
            f"- Komşuluk medyan UTPM: {comparison['neighbor_median_utpm']:.1f}",
            f"- Fark (target − komşu mean): **{comparison['vs_neighborhood']:+.1f}**",
        ]

    lines += [
        "",
        "Lütfen bu hücre için 4-6 cümlelik Türkçe planlamacı yorumu yaz.",
    ]
    return "\n".join([l for l in lines if l != ""])


def explain_with_claude(
    summary: dict,
    comparison: dict,
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 600,
) -> tuple[str, str]:
    """Claude API ile yorum üretir.

    Parameters
    ----------
    summary : dict
        ``cell_summary`` çıktısı.
    comparison : dict
        ``neighborhood_comparison`` çıktısı.
    api_key : str, optional
        Anthropic API key. ``None`` ise ``ANTHROPIC_API_KEY`` env'den okur.
    model : str
        Claude model adı.

    Returns
    -------
    (text, source) : tuple
        ``source`` = "claude" veya "fallback".
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    user_prompt = build_user_prompt(summary, comparison)

    if not api_key:
        return _fallback_template(summary, comparison), "fallback"

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = msg.content[0].text
        return text, "claude"
    except Exception as e:
        fallback = _fallback_template(summary, comparison)
        return f"{fallback}\n\n_(Claude API hatası: {type(e).__name__}: {e})_", "fallback"


def _fallback_template(summary: dict, comparison: dict) -> str:
    """API key yoksa veya hata olursa template-based yorum. Defensive — eksik keylerde de çalışır."""
    lines = []

    score = summary.get("utpm_score")
    cls = summary.get("utpm_class_label", "?")
    lst = summary.get("lst_mean")
    cluster = summary.get("lisa_cluster", "NS")

    if score is None:
        lines.append(f"Bu hücre için UTPM skoru bulunamadı (sınıf: **{cls}**). Veri kalitesi sınırlı olabilir.")
    elif score >= 60:
        lines.append(f"Bu hücre **{cls}** sınıfında (UTPM {score:.1f}/100) — ısı kalıcılığı çok yüksek, gece/sabah serinlemiyor.")
    elif score >= 44:
        lines.append(f"Hücre **{cls}** sınıfında (UTPM {score:.1f}). Isı kalıcılığı orta-yüksek, soğumakta zorlanıyor.")
    elif score >= 22:
        lines.append(f"**{cls}** sınıfı (UTPM {score:.1f}). Termal yük düşük-orta, görece serinleyebiliyor.")
    else:
        lines.append(f"**{cls}** sınıfı (UTPM {score:.1f}) — kıyı/yeşil etki belirgin, hızlı serinliyor.")

    # 2. Etkenler
    feats = summary.get("features", {})
    if feats:
        notable = []
        if feats.get("impervious_pct", 0) > 70:
            notable.append("yüksek geçirimsiz yüzey oranı (%{:.0f})".format(feats["impervious_pct"]))
        if feats.get("ndvi_mean", 1) < 0.1:
            notable.append("düşük NDVI ({:.2f}, bitki örtüsü zayıf)".format(feats["ndvi_mean"]))
        if feats.get("albedo_mean", 0) > 0.3:
            notable.append("yüksek albedo ({:.2f})".format(feats["albedo_mean"]))
        if feats.get("dtc_breeze_m", 0) > 3000:
            notable.append("kıyıdan {:.0f} m kara içi (rüzgar erişimi sınırlı)".format(feats["dtc_breeze_m"]))
        if notable:
            lines.append("Başlıca etkenler: " + ", ".join(notable[:2]) + ".")

    # 3. Persistence
    pers = summary.get("persistence", {})
    if pers:
        ytq = pers["years_in_top_quartile"]
        ybq = pers["years_in_bottom_quartile"]
        if ytq == 5:
            lines.append("5/5 yıl en sıcak quartile'da → **kalıcı sıcak alan, yıllar boyu serinlemiyor**.")
        elif ytq >= 3:
            lines.append(f"{ytq}/5 yıl en sıcak quartile'da → tutarlı sıcak hücre, çoğu yaz serinleyemiyor.")
        elif ybq >= 3:
            lines.append(f"{ybq}/5 yıl en serin quartile'da → tutarlı serin hücre, yıldan yıla rahatlıkla soğuyor.")
        else:
            lines.append("Persistence durumu karışık — yıllar arası değişken.")

    # 4. LISA
    if cluster in ("HH", "LL", "HL", "LH"):
        lines.append(f"LISA: {cluster} — {summary.get('lisa_description', '')}")

    # 5. Komşu karşılaştırma
    if comparison:
        diff = comparison["vs_neighborhood"]
        if abs(diff) >= 10:
            lines.append(f"Komşuluk ortalamasından {diff:+.1f} puan farklı (yerel anomali).")
        else:
            lines.append(f"Komşuluk ortalamasıyla uyumlu (fark {diff:+.1f}).")

    # 6. Müdahale önerisi (score None ise atla)
    if score is not None:
        if score >= 60 and feats.get("impervious_pct", 0) > 60:
            lines.append("**Öneri:** soğuk çatı boyası + sokak ağacı + yeşil bant.")
        elif score >= 44 and feats.get("ndvi_mean", 1) < 0.2:
            lines.append("**Öneri:** boş arsa yeşillendirme + cadde ağaçlandırma.")
        elif score < 22:
            lines.append("**Öneri:** mevcut yeşil/kıyı dokusunu koruyucu planlama.")

    return " ".join(lines) if lines else "Bu hücre için yorum oluşturulamadı (veri eksik)."
