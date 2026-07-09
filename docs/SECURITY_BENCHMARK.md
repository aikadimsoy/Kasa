# KASA Güvenlik Benchmark — Kanıt Raporu
2026-07-09T08:33:56, Windows-11-10.0.26200-SP0, 3.14.5
**Damga:** commit `e313846` · config-hash `27022693a685` · WebView2 `150.0.4078.48` · OS build `10.0.26200` · katman **base** · host `REDACTED-HOST`
## 🔴 YAYINA HAZIR DEĞİL (kritik açık)
| Total | PASS | FAIL | WARN | SKIP |
|-------|------|------|------|------|
| 21 | 18 | 2 | 1 | 0 |

## Authz
| ID | Başlık | Durum | Önem | Kanıt |
|----|--------|-------|-------|-------|
| AUTHZ-TOKEN-MISSING | POST with NO Authorization header | ✅ PASS | critical | `Status code: 401` |
| AUTHZ-TOKEN-WRONG | POST with header Bearer 'definitely-wrong-token' | ✅ PASS | critical | `Status code: 401` |
| AUTHZ-C5 | valid token, agent_id='system', tool profile_read parameters {'scope':'user.name'} | ✅ PASS | critical | `Status code: 403` |
| AUTHZ-C7 | valid token, agent_id='tester', tool_name='grant_permission' | ✅ PASS | high | `Status code: 404` |
| AUTHZ-C8 | valid token, agent_id='tester', tool_name='_check_permission' | ✅ PASS | high | `Status code: 404` |
| AUTHZ-DENY | valid token, agent_id='unauthz_987296', tool profile_read parameters {'scope':'user.name'} | ✅ PASS | critical | `Status code: 403` |
| AUTHZ-BIND | Static check on server binding host | ✅ PASS | high | `Default host: 127.0.0.1` |

## Crypto
| ID | Başlık | Durum | Önem | Kanıt |
|----|--------|-------|-------|-------|
| CRYPTO-EXPORT | Prove vault crypto properties (Export) | ✅ PASS | high | `Events count: 1` |
| CRYPTO-EXPORT | Prove vault crypto properties (Export) | ✅ PASS | high | `wrong-pw rejected` |
| CRYPTO-KDF | Prove vault crypto properties (Key Derivation Function) | ✅ PASS | medium | `scrypt parameters found` |
| CRYPTO-ATREST | Prove vault crypto properties (At Rest) | ❌ FAIL | critical | `plaintext canary found at byte offset 8096 in kasa.db (49152 bytes)` |
| CRYPTO-DPAPI | Prove vault crypto properties (Data Protection API) | ✅ PASS | info | `DPAPI CryptProtectData available for key file` |

## Audit
| ID | Başlık | Durum | Önem | Kanıt |
|----|--------|-------|-------|-------|
| AUDIT-VERIFY | Audit Chain Integrity Verified | ✅ PASS | high | `3-record chain verified` |
| AUDIT-TAMPER-MODIFY | Audit Chain Tamper Detection | ✅ PASS | critical | `Tampering detected in row 2` |
| AUDIT-TAMPER-DELETE | Audit Chain Deletion Detection | ✅ PASS | critical | `Deletion detected in row 2` |

## Scan
| ID | Başlık | Durum | Önem | Kanıt |
|----|--------|-------|-------|-------|
| SCAN-BANDIT | Static Analysis with Bandit | ⚠️ WARN | high | `High: 0, Medium: 5; Found MEDIUM severity issues.` |
| SCAN-PIPAUDIT | Dependency Audit with pip-audit | ✅ PASS | high | `Vulnerable dependencies: 0` |
| SCAN-SECRETS | Secret Detection with Detect-Secrets | ❌ FAIL | critical | `Total findings: 11; First file with secrets: _orch\redteam\ai_attack_test.py` |
| SCAN-BAK-HYGIENE | No backup (.bak) files under src/ | ✅ PASS | medium | `No .bak/backup files under src/` |

## Fuzz
| ID | Başlık | Durum | Önem | Kanıt |
|----|--------|-------|-------|-------|
| FUZZ-NOAUTH | Malformed unauthenticated request rejected | ✅ PASS | critical | `Status code: 401` |
| FUZZ-EXECUTE | Malformed payload robustness (execute_tool) | ✅ PASS | high | `10 malformed payloads sent, 0 caused 5xx` |

## Düzeltme Önerileri
- CRYPTO-ATREST: Enable at-rest DB encryption (SQLCipher / sqlcipher3-binary PRAGMA key, or application-layer AES-GCM on content).
- SCAN-BANDIT: pip install bandit; review src findings
- SCAN-SECRETS: Review filesystem findings

## Bilinen Sınırlar (dürüst)
- fingerprint B1/B3/B4 still open;
- non-Windows DPAPI no-op;
- this benchmark does not cover network MITM or physical access.