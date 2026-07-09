# ADR-0003 — At-rest Şifreleme Boşluğu

## Durum
Rapor Edildi

## Bağlam
- PROJECT_BRIEF §5 'SQLite + SQLCipher (tam dosya şifrelemesi)' vaat ediyor.
- PROJECT_BRIEF §9 tehdit modelinde yerel-hirsizlık (cihaz çalınması) karşı bu şifrelemeye dayanıyor.
- Ancak src/vault/database.py düz sqlite3 kullanıyor; şifreleme atlanmış.
- DPAPI, kullanılmayan bir anahtar dosyasını koruyor; bu yüzden kasa.db at-rest DÜZ METİN.
- Export .kasa dosyası doğru şekilde şifreli (AES-GCM + scrypt); ancak sadece canlı DB etkilidir.

## Karar
- KURALLAR Kural 3 (önce bildir) ve §10 (owner-gated) gereğine göre: durum RAPORLANIR, düzeltilmez.
- Benchmark bunu CRYPTO-ATREST = FAIL (kritik) olarak belgeler.
- Remediation (SQLCipher veya uygulama katmanı AES-GCM), owner kararıyla ertelenmiştir.

## Sonuçlar
- Kirik bir güvenlik veavinin duru ifası sağlanır.
- 'Yayına hazır' verdict'i remediation tamamlanana kadar bloklanır.
- Remediation yolunu ve öncelğini owner belirler.
