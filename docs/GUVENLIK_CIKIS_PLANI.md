# KASA Çıkış Noktası (Egress Governance) — Plan & Değerlendirme
_Fable 5 (şef), 2026-07-15. Sektör-Önce kuralıyla araştırıldı; KURMADAN ÖNCE plan.
Kod İngilizce + Türkçe açıklama notlu (sonrası için fayda). Kaynaklar dipte._

## 0. Amaç (kullanıcı vizyonu)
KASA bir GÜVENLİK ARACI; ancak trafik ondan geçerse işe yarar. Hedef: KASA'yı
**kontrollü çıkış noktası (egress gateway)** yapmak — çıkışta ne/nasıl gittiğini
etiketle + sızıntıyı engelle; girişte ne çekildiğini denetle; her isteğin "emrin
amacına" hizmet edip etmediğini doğrula; ve bunu baypas/kurcalamaya karşı bağımsız
ikinci katmanla çapraz-kontrol et.

## 1. Sektör nerede, biz neredeyiz, hız (dürüst)

Araştırma bulgusu: 2026'da AI-ajan güvenliğinde egress THE konu. "Egress ajanların
varsayılan kaçış kapısı oldu; egress yönetimi olmadan exfiltration normal trafik gibi
görünür." En çok ATLANAN katman da bu — yani doğru ve az-hizmet-edilen yeri hedefliyoruz.

| Yetenek | Sektör (2026) | Biz | Fark / hız |
|---|---|---|---|
| Proxy + IP/port/host allowlist | NVIDIA baseline; olgun | tasarım hazır, kurulmadı | çekirdek: birkaç saat → paritede |
| Görev-bazlı allowlist (niyet) | "signed-context egress" (Safeguard: provenance+tool-id+akıl-izi) | tasarım (deterministik allowlist) | kavramsal paritede; provenance-lite |
| Çift-yön (ingress+egress) denetim | "agent firewall" (iki yön, kimlik-sızıntısı+injection tarama) | tasarım | konsept aynı; içerik-tarama eksik |
| TLS içerik denetimi (MITM) | TLS-terminating proxy, prompt/response tarama | YOK (karar bekliyor) | burada geride; invaziv (CA sertifika) |
| Out-of-band mutabakat (baypas yakalama) | çoğu kurulumda ATLANIR | tasarım (OS−proxy=∅) | **bizim farkımız/öne çıkışımız** |
| DNS exfil skorlama | var | yok | opsiyonel ileri |
| SIEM/ölçek | kurumsal bulut | tek-makine, sıfır-bütçe, yerel | farklı lig; bizimki local-first |

**Özet:** KAVRAM/MİMARİ olarak sektör-2026 seviyesindeyiz (agent-firewall = tam bizim
tarif). UYGULAMA olgunluğunda sıfırdayız (henüz kurulmadı). NİŞİMİZ: local-first,
sıfır-token, **deterministik mutabakatla baypas-kanıtı** — ki sektörün çoğu bunu atlar.
Çekirdeğe hız: saatler. Tam parite (içerik denetimi): günler + sertifika kararı.

## 2. Plan — katmanlı (her katman kalibrasyonla mühürlenir)

### Faz 1 — Egress kapısı + niyet (deterministik, invaziv değil) ← ÖNCE
- Yerel proxy (`kasa_egress.py`): tüm araştırma trafiği `HTTP(S)_PROXY` ile buradan.
- Her istek kayıt defterine (JSONL): ts, görev-id, host, port, izin/engel, sebep, byte.
- **Görev-bazlı allowlist:** her görev meşru domainlerini bildirir; dışı = ENGEL+bayrak.
- Tracker/telemetri host blocklist (çıkış sızıntısı engelleme).
- Kabul kapısı (kalibrasyon): izinli host geçer; ekli "sahte-sızıntı" host'u ENGELLENİR.

### Faz 2 — Out-of-band mutabakat (baypas/kurcalama-kanıtı) ← bizim farkımız
- OS-seviyesi bağımsız görünüm (pktmon/`Get-NetTCPConnection`) proxy'den habersiz toplar.
- Deterministik mutabakat: **(OS-gözlemi) − (proxy-izinlisi) = ∅** olmalı. Değilse baypas.
- (Katalog "mutabakat" desenimizin ta kendisi: kaynak↔çıktı farkı=0 → burada bağlantı farkı=0.)
- Kabul kapısı: proxy'yi baypas eden ekli test-bağlantısı mutabakatta YAKALANIR.

### Faz 3 — Girişte denetim + kıyas + analiz ("chuck")
- Girişte: yanıt metadata (boyut, tip, host) → anomali (beklenmedik büyük çekme).
- Akademik/edu güncel makale bulguları ↔ KASA baseline (RESEARCH_FINDINGS.md) kıyası.
- Yerel model = Sinyal/Gürültü analisti (farkları YORUMLAR); karar deterministik.

### Faz 4 — (OPSİYONEL, owner kararı) TLS içerik denetimi (MITM)
- CA sertifika + TLS-terminate → içerik/kimlik-sızıntısı/injection taraması (agent-firewall tam).
- İnvaziv; yalnız owner açık onayıyla. "emrin dışı ince manipülasyon"u ancak bu yakalar.

## 3. Dürüst sınırlar
- MITM'siz: host/hacim düzeyi görülür, TLS-içi İÇERİK görülmez (KASA dersi: allow-list =
  namespace kapısı, içerik kapısı değil). İnce/semantik manipülasyon Faz 4 gerektirir.
- "Saklı" katman = kurcalama-ÖNLEME değil kurcalama-KANITI (admin saldırgan her şeyi alt eder).
- Proxy'yi dinlemeyen süreç baypas eder → Faz 2 tam bu yüzden var (kör-nokta kapatır).

## 4. Kod & kayıt kuralları
- Kod İngilizce tanımlayıcı + **Türkçe açıklama notu** (her modül başında ne/neden).
- Kayıt defteri: `d:\kasa\_orch\redteam\saha_testi.jsonl` (yoksa oluşturulur).
- Her faz git'e commit + bu belge güncellenir; kalibrasyon kanıtı (geçen+engellenen) saklanır.
- Deterministik karar, AI danışman — KASA çekirdek ilkesi korunur.

## 5. Başlangıç sırası (onay sonrası)
Faz 1 → kalibrasyon → Faz 2 → kalibrasyon → (Faz 3) → (Faz 4 ayrı karar).
Koşan profesör eğitimine dokunmadan; onu Faz 1 bitince `HTTP_PROXY` ile KASA'dan geçireceğiz.

## Kaynaklar
- https://safeguard.sh/resources/blog/agent-runtime-egress-controls-2026 (signed-context egress)
- https://www.deepinspect.ai/blog/ai-egress-monitoring (en çok atlanan katman)
- https://pipelab.org/agent-firewall/ (agent firewall = iki-yön runtime katman)
- https://accuknox.com/blog/runtime-ai-governance-security-platforms-llm-systems-2026
- https://www.paloaltonetworks.com/cyberpedia/data-loss-prevention-best-practices
- https://www.varonis.com/blog/dlp-zero-trust
