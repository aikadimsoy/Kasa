# Fable Şef — Profil Eğitimi Kalite Kontrol Checklist'i

> Fable-5 (şef) bu checklist'i YAZAR. Yerel işçi modeller aday fact üretir; bu checklist +
> deterministik gate onları eler. Fable canlıyken (bu oturum) survivors'ı ayrıca elle onaylar;
> Fable yokken (15-gün gözcü) checklist DETERMINISTIK olarak `enrich_campaign.py`'de uygulanır.
> İlke: son söz deterministik kuralda (AI danışman) — halüsinasyon vault'a sızmaz.

## Kapsam (yalnız bu başlıklar — mevcut namespace'ler)
- `user.preferences.*` — kalıcı ilgi/tercihler (ne sever, neye ilgi duyar)
- `user.habits.*` — tekrarlayan davranış/rutin (ne sık yapar)
- `user.profile.*` — istikrarlı kimlik/bağlam nitelikleri (dil, rol, konum-türü — SIR DEĞİL)

## Kabul kuralları (bir fact GEÇMEK için hepsini sağlamalı)
1. **Namespace**: key yukarıdaki 3 önekten biriyle başlar (aksi → RED, gate).
2. **Özgüllük**: key en az 3 nokta-parçalı (`user.<kategori>.<ad>`); `value.text` ≥ 12 karakter,
   belirsiz/genel değil ("uses internet" gibi çöp → RED).
3. **Güven**: `value.confidence` ≥ 0.55. Altı → RED (zayıf sinyal).
4. **Temellenme**: fact, gerçek ziyaret edilen domain(ler)e dayanmalı; provenance modelden
   ALINMAZ, cited sites'ın gerçek event id'lerinden DETERMINISTIK hesaplanır (eşleşme yoksa RED).
5. **Konsensüs bonusu**: ≥2 model aynı fikri önerdiyse "güçlü" etiketlenir; tek-model önerileri
   yalnız confidence ≥ 0.7 ise geçer (tek kaynak daha yüksek çıta).
6. **Güvenlik**: value/key içinde kredensiyel-benzeri ifade YOK (CREDENTIAL_DENY, gate). Sır,
   parola, admin, token, gözetim çıkarımı → RED.
7. **Tekilllik**: mevcut profildeki aynı key + aynı anlam tekrar yazılmaz (supersedes zinciri
   yalnız gerçek güncelleme için).

## Günlük tavan (makine + kalite koruması)
- Bir çalıştırmada en fazla **8** yeni/güncel fact yazılır (kalite > hacim; DoS önleme).
- Modeller **sırayla** çağrılır, aralarında soğuma; paralel ağır çıkarım YOK.

## Fable'ın canlı onayı (yalnız bu oturum)
Fable, gate'ten geçen survivors'ı okur ve şunu sorar: "Bu, sahibin gerçek verisinden çıkan,
işe yarar, isabetli bir öz-not mu?" Şüpheli/uydurma/gürültü olanı elle çıkarır. 15-gün gözcüde
bu adım yoktur → gözcü yalnız checklist+gate'e güvenir (bu yüzden çıtalar yüksek tutuldu).
