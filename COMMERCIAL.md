# Commercial Licensing — KASA

**Version 1.0 · 2026**

KASA is dual-licensed:

1. **AGPL-3.0** — the default. Free of charge, for everyone. The canonical text is in
   [`LICENSE`](LICENSE) at the repository root.
2. **Commercial license** — an alternative set of terms for people who cannot, or do not want to,
   meet the AGPL obligations. Terms are negotiated with the copyright holder.

You only need to read past this point if option 1 does not work for you.

> This document is **not legal advice**. It is a plain-language summary written by the project
> owner to explain the intent behind the license choice. Where this summary and the actual
> [`LICENSE`](LICENSE) text disagree, **`LICENSE` wins**. If the stakes are meaningful for you,
> consult your own counsel.

---

## 1. What the AGPL asks of you

The GNU Affero General Public License v3.0 is a *copyleft* license. Copyleft means: you get broad
freedom to use, study, modify, and redistribute the software, on the condition that you pass those
same freedoms on. In practice, three obligations matter:

**a. Derivative works stay AGPL.**
If you modify KASA, or combine it with your own code such that the result is a derivative work of
KASA, then when you distribute that result it must also be licensed under AGPL-3.0, with source
available to the recipients.

**b. Distributing binaries means distributing source.**
If you hand someone a compiled KASA (an `.exe`, an installer, a container image), you must also
make the Corresponding Source available to them, under the same license. See `LICENSE` sections 4-6.

**c. The network clause — AGPL section 13.**
This is the clause that distinguishes AGPL from plain GPL, and it is the one people miss.

The exact wording is in [`LICENSE`](LICENSE), lines 540-551:

> "Notwithstanding any other provision of this License, if you modify the Program, your modified
> version must prominently offer all users interacting with it remotely through a computer network
> (if your version supports such interaction) an opportunity to receive the Corresponding Source of
> your version by providing access to the Corresponding Source from a network server at no charge
> [...]"

Read plainly: **if you run a modified KASA as a network service, "I never shipped a binary" is not
a defense.** Your remote users are entitled to your source. Merely *using* the software over a
network does not by itself trigger section 13 — the trigger is offering a **modified** version to
remote users. But the practical effect for a SaaS operator is the same: you cannot build a private
fork, put it behind an API, and keep the changes to yourself.

A note on how this interacts with KASA specifically: KASA is a local-first vault, and its MCP server
binds to loopback by default — `host="127.0.0.1"` is hardcoded in the desktop launch path
(`src/desktop/launch.py:164`) and is the default argument of `start_server()`
(`src/mcp_server/server.py:241`). In the ordinary single-user desktop case there are therefore no
"remote users" for section 13 to reach. Note that `start_server()` accepts a different host from its
caller, so this is a default, not an enforced constraint. Section 13 becomes relevant the moment
someone takes KASA off the desktop and exposes a modified version to other people over a network.

---

## 2. You probably do NOT need a commercial license

Most people reading this can stop here and just use KASA under the AGPL. **No commercial license is
required for:**

- **Personal use.** Running KASA on your own machine, for your own memory, forever, for free. This
  is the case the project was built for.
- **Education and teaching.** Classroom use, coursework, student projects.
- **Research.** Academic or independent, including publishing your results.
- **Evaluation.** Trying KASA out inside a company to decide whether it fits — including internal
  pilots — before any decision to deploy or ship.
- **Open-source projects that comply with the AGPL.** If your project is itself AGPL-3.0 (or is
  licensed such that AGPL-3.0 obligations are satisfied for your users), you are welcome here and
  you owe nothing. Build on KASA. Fork it. Send patches.
- **Private modifications you never distribute.** You can change KASA however you like for your own
  use; the obligations attach on distribution, and on network use of a modified version.

The point of the dual license is *not* to squeeze individuals. Individuals are the reason the
project exists. The commercial track exists so that companies who want to close the source pay for
that privilege instead of taking it.

---

## 3. You DO need a commercial license if

**a. You are embedding KASA, or a derivative of it, in a closed-source product.**
You want to ship KASA's vault, permission broker, or MCP layer inside something you distribute
without source. AGPL does not permit this. A commercial license can.

**b. You cannot meet the AGPL obligations for corporate or internal reasons.**
Some organizations cannot release derived source — policy, contractual obligations to a customer,
regulatory constraints, or code that is genuinely commingled with proprietary systems. If your
internal or customer-facing deployment involves modifications you are not able to publish, and
especially if that deployment is reachable over a network by other users, you need the commercial
track.

**c. You want to redistribute under terms other than the AGPL.**
Reselling, white-labeling, OEM bundling, sublicensing to your own customers, or shipping under your
own license terms. All of these require permission from the copyright holder.

**d. You need contractual terms the AGPL does not provide.**
AGPL software is supplied "as is", with no warranty and no indemnity (see `LICENSE` sections 15-16).
If your procurement process requires warranty, indemnification, a support commitment, or a named
counterparty on a contract, that is a commercial conversation, not a license-file conversation.

If you are unsure which side of this line you fall on, ask. Asking is free and nobody has ever been
penalized for asking.

---

## 4. What a commercial license does and does not change

A commercial license changes **your obligations**. It does not change the software's behavior, and
it does not change the project's principles.

Specifically, what does **not** change under any license:

- KASA remains local-first. The commercial track is not a hosted or cloud edition.
- There is no "premium" build with capabilities withheld from AGPL users. The AGPL edition is the
  whole product.
- Documented security properties are documented identically for both tracks. No claim is made to a
  paying customer that is not made in the public repository, and every claim in either place is tied
  to a measurement or is not written at all.

---

## 5. Terms and pricing

**Terms are subject to discussion.**

No price list, tier structure, or standard contract is published here, and none is implied. Scope,
deployment shape, and support expectations vary enough that quoting a number in advance would be
inventing one. Bring your use case and the terms get worked out from there.

---

## 6. How to get in touch

<!-- PLACEHOLDER: repository owner must replace this with a real contact channel before the
     repository goes public. Do not ship this file with the placeholder still in it. -->

**Contact the repository owner via GitHub** — open an issue on the KASA repository, or use the
contact channel listed on the repository's profile.

When you write, the following makes the conversation faster:

- What you are building, and where KASA sits inside it.
- Whether you are modifying KASA or using it as-is.
- Whether the deployment is internal, customer-facing, or redistributed.
- Which specific AGPL obligation is the blocker for you.

---

## 7. Contributions and copyright

Dual licensing only works if every part of the work can be distributed under both sets of terms. If
a contributed patch could be distributed only under the AGPL, the project owner could offer the AGPL
edition but could **not** offer any commercial license covering that code — each contributor would
separately hold a veto over it.

So contributions carry a license grant: by sending a pull request, you accept that your contribution
may be distributed under both AGPL-3.0 and the owner's commercial terms. **Your copyright stays with
you — you are not assigning it**, and there is no signed CLA document to execute; this is a plain
statement of terms, not a contract. The authoritative wording is
[`CONTRIBUTING.md`](CONTRIBUTING.md) section 5 — read it before sending a patch.

To be explicit about the trade: **this is a real ask of contributors**, and it is stated up front
rather than buried. In exchange, the AGPL edition stays complete and free, permanently. If you do
not accept it, open an issue describing the idea instead of sending code.

---

## 8. Third-party components

KASA depends on third-party software that is **not** covered by this dual license. Those components
remain under their own licenses, and a commercial license for KASA grants you no rights whatsoever
in them. See [`NOTICE`](NOTICE) for the inventory.

One item deserves attention before you plan a closed-source product: **PyQt5 is under GPL v3** per
its installed package metadata. Its own licensor offers a separate commercial track, and a KASA
commercial license does not and cannot relicense it.

The scope of that exposure, measured rather than assumed: inside `src/`, PyQt5 is imported only by
the system-tray helper (`src/tray/app.py:3-5`). The desktop UI is pywebview over WebView2
(`src/desktop/launch.py:172`, `src/browser/browser_window.py:1`), not Qt. The packaging script
excludes Qt from the build (`--nofollow-import-to=PyQt5,PyQt6,PySide2,PySide6,tkinter` —
`build_kasa.ps1:62`) and does not list `src.tray` among the packaged packages
(`build_kasa.ps1:70-75`; rationale in `docs/EXE_PACKAGING_LOG.md:111`). An executable produced by
that script therefore does not ship PyQt5.

That is a statement about the current build script, not a permanent property of the project. If you
re-enable the tray component, or package KASA yourself with different flags, the GPL v3 obligation
is yours to resolve — either with PyQt5's licensor, or by not shipping that component.

---

## 9. Attribution

Copyright and authorship attribution for KASA remains with the project owner and stays in the
repository under every license track. See [`NOTICE`](NOTICE).

---

## Türkçe özet

Bu bölüm yukarıdaki İngilizce metnin özetidir. **Bağlayıcı metin İngilizce olanıdır**; bir çelişki
olursa İngilizce bölüm ve `LICENSE` dosyası geçerlidir. *Bu belge hukuki danışmanlık değildir.*

**KASA çift lisanslıdır.** Varsayılan lisans **AGPL-3.0**'dır ve ücretsizdir; kanonik metin depo
kökündeki [`LICENSE`](LICENSE) dosyasındadır.

**AGPL ne ister?** Üç şey: (1) KASA'dan türettiğiniz çalışmalar da AGPL olmalıdır; (2) derlenmiş bir
sürümü birine verirseniz kaynağını da vermeniz gerekir; (3) **13. madde** — *değiştirilmiş* bir
sürümü ağ üzerinden kullanıcılara sunuyorsanız, o kullanıcılara kaynağı sunmak zorundasınız
(`LICENSE` satır 540-551). Yani "ikili dağıtmadım, sadece servis olarak sundum" bir savunma değildir.
Sadece *kullanmak* 13. maddeyi tetiklemez; tetikleyen, değiştirilmiş sürümü uzaktaki kullanıcılara
açmaktır. KASA yerel-öncelikli çalıştığı ve MCP sunucusu varsayılan olarak `127.0.0.1`'e bağlandığı
için (`src/desktop/launch.py:164`, `src/mcp_server/server.py:241`), sıradan tek kullanıcılı masaüstü
senaryosunda 13. maddenin ulaşacağı "uzak kullanıcı" yoktur. Bunun bir *varsayılan* olduğunu, zorunlu
bir kısıt olmadığını not edin: `start_server()` çağırandan farklı bir host alabilir.

**Ticari lisansa İHTİYACI OLMAYANLAR** (çoğu kişi buradadır ve okumayı burada bırakabilir):
bireysel kullanım, eğitim, araştırma, değerlendirme/deneme ve AGPL'e uyan açık kaynak projeler.
Ayrıca hiç dağıtmadığınız özel değişiklikler. Bunun için hiçbir ücret ödemezsiniz ve ödemeniz de
beklenmez — proje zaten bireysel kullanıcı için yazıldı.

**Ticari lisansa İHTİYACI OLANLAR:** (a) KASA'yı veya türevini **kapalı kaynak** bir ürüne gömenler;
(b) kurumsal/iç kullanımda AGPL yükümlülüklerini yerine getiremeyecek olanlar; (c) AGPL dışı
şartlarla yeniden dağıtmak, satmak, white-label yapmak isteyenler; (d) garanti, tazminat veya
sözleşmeli destek gibi AGPL'in vermediği şartlara ihtiyaç duyanlar.

**Ticari lisans neyi değiştirir?** Yalnızca sizin yükümlülüklerinizi. Yazılımın davranışını
değiştirmez: gizlenmiş özellik içeren "premium" bir sürüm yoktur, AGPL sürümü ürünün tamamıdır ve
güvenlik beyanları her iki tarafta da aynıdır.

**Fiyat ve şartlar görüşmeye tabidir.** Burada yayımlanmış bir fiyat listesi yoktur; uydurulmuş bir
rakam da yoktur.

**İletişim:** Depo sahibine GitHub üzerinden ulaşın — depoda issue açarak veya deponun profilinde
yazan iletişim kanalıyla.

**Katkı ve telif:** Çift lisansın çalışabilmesi için işin her parçasının her iki lisans altında da
dağıtılabilir olması gerekir; aksi halde katkı içeren kod için ticari lisans verilemez, her katkıcı
ayrı ayrı veto sahibi olur. Bu nedenle katkı bir lisans izni taşır: pull request gönderdiğinizde,
katkınızın hem AGPL-3.0 hem de sahibin ticari şartlarıyla dağıtılabileceğini kabul etmiş olursunuz.
**Telif hakkınız sizde kalır — devretmiyorsunuz** ve imzalanacak resmî bir CLA metni yoktur; bu bir
sözleşme değil, sade bir şart beyanıdır. Bağlayıcı ifade
[`CONTRIBUTING.md`](CONTRIBUTING.md) dosyasının 5. bölümündedir. Bu katkıcıdan gerçek bir taleptir ve
saklanmadan yazılmıştır; karşılığında AGPL sürümü kalıcı olarak eksiksiz ve ücretsiz kalır.

**Üçüncü taraf bileşenler** bu çift lisansın kapsamı DIŞINDADIR; kendi lisanslarına tabidir
([`NOTICE`](NOTICE)). Özellikle **PyQt5 kendi paket meta verisine göre GPL v3'tür** ve KASA'nın
ticari lisansı onu yeniden lisanslayamaz. Kapsamı ölçülmüş haliyle: `src/` içinde PyQt5'i yalnızca
sistem tepsisi yardımcısı kullanır (`src/tray/app.py:3-5`); masaüstü arayüzü Qt değil,
WebView2 üzerinde pywebview'dır (`src/desktop/launch.py:172`). Paketleme betiği Qt'yi build dışında
bırakır (`build_kasa.ps1:62`) ve `src.tray`'i paketlemez (`build_kasa.ps1:70-75`), dolayısıyla o
betiğin ürettiği exe PyQt5 içermez. Bu, projenin kalıcı bir özelliği değil mevcut build betiğinin
durumudur: tepsi bileşenini geri açarsanız veya kendi bayraklarınızla paketlerseniz GPL v3
yükümlülüğü sizindir.
