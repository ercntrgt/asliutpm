"""Claude API yorumlama modülü — fallback template ile."""
from __future__ import annotations

import os
from typing import Optional


SYSTEM_PROMPT = """Sen Antalya Konyaaltı için geliştirilmiş UTPM (Urban Thermal Persistence Model)
kararı destek asistanısın. Kullanıcı haritada bir 30 m grid hücresi seçer; sen o hücrenin
LST/UTPM/persistence/komşuluk verisini analiz edip Türkçe, sade, planlamacı dilinde 4-6 cümlelik
bir yorum yazarsın.

Yorumun şu yapıyı izlesin:
1. Bu hücrenin termal durumunu **bir cümle** ile özetle (sıcak/orta/serin + UTPM sınıfı).
2. Hangi 1-2 fiziksel **etken** (albedo, NDVI, kıyı mesafesi, geçirimsiz yüzey, bina yoğunluğu)
   bu durumdan sorumlu? Veriden destekli yorum yap.
3. **Persistence** ne diyor? 5 yıl içinde kaç yıl en sıcak quartile'da olduğu önemli — 5/5 ise
   "kalıcı UHI çekirdeği".
4. **LISA cluster** durumunu yorumla (HH = UHI çekirdeği, LL = serin ada, NS = anlamsız).
5. **Komşu karşılaştırma**: hücre çevresine göre nasıl?
6. **Müdahale önerisi**: 1 cümle (yeşillendirme, soğuk çatı, gölge ağaç, vb.)

Klişe ifadelerden kaçın. Sayıları kullan. Doğrudan gerçeği aktar."""


def build_user_prompt(summary: dict, comparison: dict) -> str:
    """Hücre verisinden Claude'a gönderilecek user mesajını üretir."""
    feats = summary.get("features", {})
    pers = summary.get("persistence", {})

    lines = [
        f"30 m grid hücresi: `{summary['cell_id']}`",
    ]
    if "mahalle" in summary:
        lines.append(f"Mahalle: {summary['mahalle']}")
    lines += [
        "",
        f"## Termal durum",
        f"- LST (5-yıl medyan): **{summary.get('lst_mean', 'N/A'):.2f} °C**" if summary.get('lst_mean') else "",
        f"- UTPM skoru (0-100): **{summary['utpm_score']:.1f}**",
        f"- UTPM sınıfı: **{summary['utpm_class_label']}** (Jenks {summary['utpm_class']+1}/5)",
        f"- LISA cluster: **{summary['lisa_cluster']}** — {summary['lisa_description']}",
        f"- Local Moran I: {summary['local_I']:.3f} (p={summary['lisa_p']:.3f})",
        "",
        "## Fiziksel özellikler",
    ]
    if feats:
        for k, v in feats.items():
            if v is not None:
                lines.append(f"- {k}: {v:.3f}")

    if pers:
        lines += [
            "",
            "## 5-yıl persistence",
            f"- Yıllık ortalama LST: {pers.get('yearly_mean_lst', 'N/A'):.2f} °C" if pers.get('yearly_mean_lst') else "",
            f"- Yıllar arası std: {pers.get('yearly_std_lst', 'N/A'):.2f} °C" if pers.get('yearly_std_lst') else "",
            f"- 5 yılda en sıcak quartile'da olduğu yıl sayısı: **{pers['years_in_top_quartile']}/5**",
            f"- 5 yılda en serin quartile'da olduğu yıl sayısı: {pers['years_in_bottom_quartile']}/5",
        ]

    if "priority" in summary:
        pr = summary["priority"]
        nice = pr["label"].split("_", 1)[1].replace("_", " ").title()
        lines += [
            "",
            "## Karar Önceliği",
            f"- Sınıf: **{nice}** (UTPM tier {pr['utpm_tier']}/2, Blockage tier {pr['block_tier']}/2)",
            f"- Wind blockage index: {pr['wind_blockage_index']:.3f}" if pr['wind_blockage_index'] else "",
        ]

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
    """API key yoksa veya hata olursa template-based yorum."""
    lines = []

    score = summary["utpm_score"]
    cls = summary["utpm_class_label"]
    lst = summary.get("lst_mean")
    cluster = summary["lisa_cluster"]

    # 1. Termal durum
    if score >= 60:
        lines.append(f"Bu hücre **{cls}** sınıfında (UTPM {score:.1f}/100) — kentsel ısı adası riski yüksek.")
    elif score >= 44:
        lines.append(f"Hücre **{cls}** sınıfında (UTPM {score:.1f}). Termal stres orta-yüksek.")
    elif score >= 22:
        lines.append(f"**{cls}** sınıfı (UTPM {score:.1f}). Termal yük düşük-orta.")
    else:
        lines.append(f"**{cls}** sınıfı (UTPM {score:.1f}) — kıyı/yeşil etki belirgin.")

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
            lines.append(f"5/5 yıl en sıcak quartile'da → **kalıcı UHI çekirdeği**.")
        elif ytq >= 3:
            lines.append(f"{ytq}/5 yıl en sıcak quartile'da → tutarlı sıcak hücre.")
        elif ybq >= 3:
            lines.append(f"{ybq}/5 yıl en serin quartile'da → tutarlı serin hücre.")
        else:
            lines.append("Persistence durumu karışık — yıllar arası değişken.")

    # 4. LISA
    if cluster in ("HH", "LL", "HL", "LH"):
        lines.append(f"LISA: {cluster} — {summary['lisa_description']}")

    # 5. Komşu karşılaştırma
    if comparison:
        diff = comparison["vs_neighborhood"]
        if abs(diff) >= 10:
            lines.append(f"Komşuluk ortalamasından {diff:+.1f} puan farklı (yerel anomali).")
        else:
            lines.append(f"Komşuluk ortalamasıyla uyumlu (fark {diff:+.1f}).")

    # 6. Müdahale önerisi
    if score >= 60 and feats.get("impervious_pct", 0) > 60:
        lines.append("**Öneri:** soğuk çatı boyası + sokak ağacı + yeşil bant.")
    elif score >= 44 and feats.get("ndvi_mean", 1) < 0.2:
        lines.append("**Öneri:** boş arsa yeşillendirme + cadde ağaçlandırma.")
    elif score < 22:
        lines.append("**Öneri:** mevcut yeşil/kıyı dokusunu koruyucu planlama.")

    return " ".join(lines)
