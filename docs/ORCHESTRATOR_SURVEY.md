# Ajan Orkestratörleri Araştırması — Model Seçimi + Araç Kullandırma + Çok-Ajan

> Tarih: 2026-07-10 · Hazırlayan: Fable-5 (şef) · Amaç: "KASA'ya model seçimi ekleyip
> KASA'yı [modele] kullandırtabilir miyiz?" sorusuna zemin + açık-kaynak manzara listesi.
> Kaynaklar: canlı web taraması (aşağıda) + Claude Code birinci-el mimari bilgisi.

---

## 0. Kısa cevaplar (yönetici özeti)

**S1: Model seçimi ekleyip KASA'yı kullandırtabilir miyiz?**
**EVET — altyapının yarısı zaten var.** Tarayıcıda model seçici çalışıyor
(`browser_window.py` → `set_model/get_model/list_models`, damıtma/bekçi beynini seçiyor).
Eksik olan tek katman: seçilen modele KASA araçlarını **tool-calling** şemasıyla sunan köprü
(aşağıda §5). Yerel modellerin (qwen2.5, deepseek, hermes3) tool-calling desteği değişken —
qwen2.5 iyi, deepseek kısmi; bu yüzden köprü "araç çağrısı üretemeyen model için JSON-çıktı
kalıbı" yedeğiyle tasarlanmalı.

**S2: "Seni IP ile buraya çağırabilir miyim?"**
**Hayır — ben bir IP'de host edilemem.** Claude modeli Anthropic bulutunda çalışır; yerel
modellerin aksine (`127.0.0.1:11434` gibi) indirilip KASA'nın yanına konamaz. Ama **üç resmi
kapım var** (hepsi "farklı bir key/token ile" sorusunun cevabı):

| Kapı | Nasıl | Kimlik | Maliyet |
|---|---|---|---|
| **Claude Code CLI (şu an)** | `claude -p "..."` headless; script/KASA süreci çağırabilir | Mevcut oturum girişi | Plan dahilinde |
| **Claude Agent SDK** (Python/TS) | KASA içinden programatik ajan döngüsü | `ANTHROPIC_API_KEY` | API token ücreti |
| **Anthropic API** (doğrudan) | `api.anthropic.com/v1/messages`, model=`claude-opus-4-8` | `ANTHROPIC_API_KEY` | API token ücreti |

**Ters yön** ("Claude KASA'yı kullansın"): Claude Code bir **MCP istemcisidir**. AMA dikkat —
bugünkü tespit: KASA'nın "MCP sunucusu" **adına rağmen gerçek MCP protokolü konuşmuyor**
(REST/FastAPI: `/v1/ingest`, `execute_tool`; `jsonrpc`/`tools/list` yok). Claude Code'un
bağlanabilmesi için ince bir **MCP adaptörü** gerekir (FastMCP ile mevcut VaultTools'u sarmak;
authz katmanı aynen korunur). Bu yapılırsa `claude mcp add` ile ben KASA araçlarını doğrudan
kullanırım.

**Güvenlik değişmezi (pazarlıksız):** Bulut modele (bana dahil) vault verisi = air-gap ihlali.
Hangi model seçilirse seçilsin veri **read-through-redact sınırından** geçer; bulut modele
yalnız maskeli/aggregate veri gider; son söz deterministik yargıçta (AI danışman kalır).
Red-team dersi: allow-list = namespace kapısı, İÇERİK kapısı DEĞİL — modele araç vermek
semantic-injection yüzeyini büyütür; içerik kapısı köprüde zorunlu.

---

## 1. Kategori A — Çok-modelli sohbet UI'ları (model seçici + araç)

| Uygulama | Teknoloji | Araçları nasıl yapmışlar | Model seçimi | Yorum |
|---|---|---|---|---|
| **LibreChat** | Node/React, MongoDB+MeiliSearch | **MCP tool sunucuları** + OpenAI-stili eklentiler + kod yorumlayıcı; ajan başına araç ataması | 15+ sağlayıcı tek panelde (OpenAI/Anthropic/Gemini/Ollama/Groq...); konuşma ortasında model değiştirme | MCP desteği en olgun; tam stack ağır (2GB+ Mongo+Meili) |
| **Open WebUI** | Python/Svelte | **Pipelines/Functions** (Python eklenti), OpenAPI araç sunucuları, MCP (mcpo proxy üzerinden) | Yerel-öncelikli; en iyi Ollama önyüzü; "model agents" = model + talimat + araç + bilgi sarmalı | Yerel kullanıcı için en hızlı kurulum; MCP native değil |
| **AnythingLLM / LobeChat / Jan** | çeşitli | Agent skills / eklenti pazarı | çoklu sağlayıcı | Aynı desenin varyantları; öne çıkan yenilik yok |

**KASA'ya ders:** "model seçici + o modele araç + talimat sarmalı" deseni endüstri standardı
("model agents"). KASA'nın seçicisi zaten var; eksik = araç sarmalı.

## 2. Kategori B — Çok-ajan çerçeveleri ("tartıştıran" uygulamalar)

| Çerçeve | Orkestrasyon modeli | Tartışma/debate | Yorum |
|---|---|---|---|
| **LangGraph** | Yönlü graf + koşullu kenarlar; checkpoint/time-travel | Graf düğümleri arası döngü ile | 2026'da yıldızda CrewAI'ı geçti; enterprise + human-in-the-loop güçlü; öğrenmesi dik |
| **AutoGen (AG2)** | **Konuşmalı GroupChat** — ajanlar sohbet odasında tartışır | Native (asıl "tartıştıran" bu) | Microsoft odağı Agent Framework'e kaydı; bakım modu sinyali |
| **CrewAI** | Rol-tabanlı ekipler (crew) + süreç tipleri | Rol diyaloğuyla dolaylı | En düşük öğrenme eğrisi (~20 satır); 5.2M aylık indirme; katı kalıp |
| **OpenAgents** | Ağ-arası ajan | MCP + **A2A** ikisine de native | Protokol-birlikte-çalışırlık iddiası |
| **smolagents / PydanticAI** | Kod-ajan / tip-güvenli | — | Hafif alternatifler |

**KASA'ya ders:** KASA'nın güvenlik döngüsü (`_orch/loop/`: deepseek üretir → qwen inceler →
deterministik gate) **zaten bir çok-ajan tartışma deseni** — CrewAI/AutoGen'in yaptığının
ev-yapımı, hedefe-özel hâli. Çerçeve ithal etmek şart değil; desen doğru.

## 3. Kategori C — Kodlama ajanları (Claude Code'un akrabaları)

| Ajan | Dil/Çekirdek | Araç mimarisi | MCP |
|---|---|---|---|
| **Claude Code** | (kapalı istemci, açık SDK) | Aşağıda §4 — referans anatomi | İstemci: native |
| **Goose** (Block→Linux Foundation) | Rust | **Her şey MCP extension'ı** (70+); host/client/server üçlüsü | En derin entegrasyon; 15+ sağlayıcı, Ollama dahil |
| **Cline / Roo Code** | VS Code eklentisi | Dosya+terminal+headless tarayıcı+MCP | First-class |
| **OpenHands** | Python | Sandbox runtime + event stream | Var |
| **Aider** | Python | Repo-map + edit formatları (diff) | Kısmi |

**Ortak mimari (hepsinde aynı):** "**Harness**" = modelin etrafındaki iskele: dosya okur, araç
çağırır, kabuk komutu koşar, sonucu modele geri besler. **Model düşünür; harness sürer.**
KASA köprüsü de tam bu olacak: KASA-harness (araç döngüsü) + seçilen model (beyin).

## 4. Referans anatomi — Claude Code "kullanma direktifleri" nasıl çalışıyor (birinci-el)

Kullanıcının işaret ettiği "sende bir uygulama var, direktifler/talimatlar her zaman vardır"
gözlemi doğru. Katmanlar (KASA köprüsüne şablon olsun diye):

1. **Sistem direktifi (system prompt):** kimlik, güvenlik sınırları, araç-kullanım kuralları,
   ortam bilgisi (cwd, OS, tarih). Her oturumda sabit enjekte edilir.
2. **Araç şemaları (JSONSchema):** her aracın adı + açıklaması + parametre şeması modele
   fonksiyon-tanımı olarak verilir; model araç çağrısını JSON üretir, harness koşar, sonucu
   mesaj olarak geri verir. (KASA köprüsünde VaultTools şemaları aynen böyle sunulur.)
3. **İzin modları + hook'lar:** her araç çağrısı kullanıcı-seçimli izin katmanından geçer;
   hook'lar çağrıyı kesebilir. → KASA karşılığı: **deterministik yargıç** (AI danışman,
   karar kural motoru) + owner-gate.
4. **Bellek/talimat dosyaları:** CLAUDE.md, memory dizini — kalıcı direktifler her oturum
   bağlama yüklenir. → KASA karşılığı: profil + talimat hücreleri.
5. **Alt-ajanlar (.claude/agents/*.md) + skills:** ayrı sistem-promptlu, kısıtlı araç-setli
   uzman ajanlar; ana ajan bunları görevle çağırır. → KASA güvenlik döngüsündeki
   deepseek-üretici/qwen-denetçi rolleriyle birebir aynı desen.
6. **MCP istemcisi:** dış araç sunucularına bağlanır (`claude mcp add`); araçlar
   `mcp__sunucu__araç` adıyla şemaya katılır.

## 5. KASA'ya haritalama — "model seçimi + KASA'yı kullandırt" mimarisi

**Var olan:** model seçici (tarayıcı UI) · VaultTools (araç seti) · bearer+authz ·
read-through-redact · deterministik gate · güvenlik döngüsü (çok-ajan).

**Eksik (yapılacak tek parça): Araç Köprüsü (tool-calling harness)**
```
seçilen model (yerel: qwen2.5/deepseek/hermes3 | bulut: Claude via key [owner-gated])
        │  (tool-calling JSON şeması: VaultTools alt-kümesi, İÇERİK-kapılı)
        ▼
KASA harness: araç çağrısını doğrula → deterministik yargıç → VaultTools koş
        │  (sonuç redact sınırından geçer; bulut modele yalnız maskeli/aggregate)
        ▼
sonucu modele geri besle → döngü
```
Uygulama notları:
- Köprü kodu = yerel işçiler (deepseek→qwen), sıfır-token; şema+güvenlik kapısı tasarımı = şef/opus.
- Yerel model tool-calling zayıfsa: kısıtlı JSON-çıktı kalıbı + deterministik ayrıştırıcı yedeği.
- Bulut model (Claude) seçeneği: `ANTHROPIC_API_KEY` ile; **owner-gated** (gelişmiş kademe) +
  yalnız redact-sonrası veri; varsayılan HER ZAMAN yerel.
- Claude Code'un KASA'yı kullanması ayrı yol: **gerçek MCP adaptörü** (FastMCP sarmalı) —
  bugünkü REST sunucu MCP protokolü konuşmuyor (tespit: 2026-07-10, `jsonrpc`/`tools/list` yok).

**Sıra önerisi (şef):** (1) MCP adaptörü [küçük, Claude Code hemen bağlanır, mevcut authz'ı
sömürür] → (2) yerel-model araç köprüsü [asıl ürün özelliği] → (3) bulut-model seçeneği
[owner-gated, en son].

---

## 6. UYGULANDI (2026-07-10) — köprü + adaptör + panel inşa edildi
Bu araştırmanın önerdiği sıra uygulandı (plan: jolly-riding-gadget.md):
- **MCP adaptörü** (`src/mcp_adapter/`, resmi `mcp` SDK MIT, exe-DIŞI): stdio → REST proxy;
  6 PUBLIC_TOOLS'u MCP olarak sunar, mevcut authz aynen korunur. `claude mcp add kasa -- py -3.12 -m src.mcp_adapter`.
- **Ajan köprüsü** (`src/agent/`): gate.py (elle carve-out — ad allow-list + İÇERİK kapısı +
  bütçe sınırları) · harness.py (elle carve-out — sınırlı tool-calling döngüsü, her çağrı
  gate'ten geçer, sonuç redact+sanitize) · routes.py + store.py (yerel-model üretimi). Araç
  yüzeyi = maskeli pano fonksiyonları (salt-okunur); ham VaultTools modele KAPALI.
- **"Ajan" paneli** (5. görünüm): model seçici + sohbet + görünür araç-izleri.
- **Kanıt:** 36 yeni test (gate 15 + köprü 12 + adaptör 9), tam suite 171 passed;
  CANLI qwen2.5:7b smoke PASS (model kasa_stats çağırdı, ham sır sızmadı).
- **Not (tespit çözüldü):** "KASA MCP konuşmuyor" bulgusu adaptörle giderildi (sunucu REST
  kaldı, adaptör MCP'yi ekledi — sıfır sunucu değişikliği).

## Kaynaklar (canlı tarama, 2026-07)
- Çok-ajan çerçeveleri: gurusup.com/blog/best-multi-agent-frameworks-2026 · openagents.org/blog (framework karşılaştırma) · turing.com/resources/ai-agent-frameworks · firecrawl.dev/blog/best-open-source-agent-frameworks
- UI'lar: docs.openwebui.com/alternatives/librechat · requesty.ai/blog/openwebui-vs-librechat · portkey.ai/blog/librechat-vs-openwebui · blog.elest.io (LibreChat/OpenWebUI/LobeChat)
- Kodlama ajanları/MCP: mcp.directory/blog/goose-vs-cline-vs-aider-vs-claude-code-vs-opencode-2026 · dev.to (goose extension system deep dive) · pinggy.io/blog/best_open_source_cli_coding_agents · frontman.sh/blog/best-open-source-ai-coding-tools-2026
