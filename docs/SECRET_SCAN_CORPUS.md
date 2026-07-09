# Secret-Tarama Kapsam Manifesti (L1)

**Tarih:** 2026-07-09 · **Mekanizma:** `tools/security_bench/checks/scan.py` → SCAN-SECRETS

## 1. Ne taranıyor (kapsam)
- Komut: `detect-secrets scan --all-files --exclude-files \.pytest_cache`, çalışma dizini `d:/kasa`.
- `--all-files` = `d:/kasa` ağacındaki **tüm** dosyalar (git-izlensin izlenmesin). Şunları kapsar:
  - kaynak (`src/`), araçlar (`tools/`), testler, dokümanlar,
  - **kasa.db** (vault, repo kökünde),
  - **`_orch/sef_monitor/`** çıktıları, **`_orch/redteam/`** fixture'ları, `_orch/loop/` pipeline'ları,
  - repo-içi log/artefakt dosyaları.
- Hariç: `.pytest_cache` (sabit `CACHEDIR.TAG` → sürekli false-positive).

## 2. Kapsam DIŞI (dürüst sınır — rezidüel)
`--all-files` yalnız `d:/kasa` ağacını görür. **Repo dışındaki** runtime artefaktları OTOMATİK taranmaz:
- OS crash-dump'ları (WER, `%LOCALAPPDATA%`), `%TEMP%` geçici dosyaları,
- kullanıcı-profili altındaki olası harici log/kopyalar.
→ Bunlar bilinçli sınır; gerekirse ayrı bir tarama hedefi eklenir (bugün kapsam dışı, gizlenmiyor).

## 3. Mekanizma: sezgisel tarama → deterministik allowlist → gerçek bulgu
detect-secrets **yüksek-duyarlık/düşük-kesinlik** entropi+keyword tarayıcısıdır; sır'a *benzeyen* her şeyi işaretler. Ham çıktı, **insan-gerekçeli** `tools/security_bench/secret_allowlist.json` ile süzülür:
- allowlist'teki `(path, type)` çiftleri **bastırılır** (yazılı gerekçeyle),
- kalan = **gerçek/denetlenmemiş** → SCAN-SECRETS FAIL.
- **Karar deterministiktir; hiçbir model bastırma kararı vermez** (bkz. plan §2 ilke 11: AI danışman, deterministik kural yargıç).

## 4. Triage (2026-07-09) — 11 ham bulgu → 10 bastırıldı (gerekçeli) + 1 gerçek
| # | Bulgu | Sınıf | Gerekçe |
|---|---|---|---|
| 1 | `kasa.toml:4` [Base64 HE] | **GERÇEK** (bastırılmadı) | bearer_token; owner-only ACL yapıldı, rotasyon+DPAPI-wrap owner-gated → **FAIL kalıyor** |
| 2 | `tools/security_bench/run.py:43` [Base64 HE] | false-positive | public WebView2 Runtime GUID, secret değil |
| 3-4 | `browser_config.json:1` [Hex HE] ×2 | false-positive | `adv_pw` PBKDF2 salt+hash (verifier, düz parola değil) |
| 5 | `_orch/redteam/ai_attack_test.py:53` [Secret Keyword] | fixture | `api_key_env` = ENV **adı**, değer değil |
| 6-7 | `_orch/redteam/ai_test_auth.json:1` [Hex HE] ×2 | fixture | red-team auth test verisi |
| 8 | `_orch/redteam/ai_test_config.example.json:20` [Secret Keyword] | fixture | örnek/placeholder |
| 9-11 | `_orch/redteam/aitest_draft.txt`, `aitest_review.txt`, `aitest_pipeline.py` [Secret Keyword] | fixture | red-team model-çıktı/pipeline |

## 5. Negatif-vaka güvencesi (sürekli kanıt)
`tests/test_secret_scan_allowlist.py` (5 test) kanıtlar:
- gerçek bearer_token allowlist ile bile **asla bastırılamaz**,
- allowlist boşsa **fail-closed** (hiçbir şey bastırılmaz),
- allowlist dışı yola sahte secret → **FAIL**,
- allowlist'li dosyada **farklı tip** yeni secret → **yakalanır**.

## 6. Açık kalan (owner-gated)
- `bearer_token` düz metin diskte: ACL mitigasyonu var; kalıcı çözüm = rotasyon (Grace-Period) + DPAPI-wrap/at-rest → owner onayı bekliyor.
