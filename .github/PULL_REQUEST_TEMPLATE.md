## What this PR changes

<!-- One paragraph. What behaviour is different after this PR? -->

## Why

<!-- The problem this solves. Link an issue if there is one. -->

## How it was verified

<!--
Name the measurement, not the intention. Examples:
  - "pytest tests/ -q --ignore=tests/browser -> 118 passed, 2 skipped (local, py3.12)"
  - "new test tests/test_x.py:42 fails on the old code, passes on the new (FAIL->PASS delta)"
  - "not verified beyond import; needs owner run on hardware with WebView2"
"I checked it" is not a measurement.
-->

## Checklist

- [ ] **No security claim without a measurement.** Nothing in this PR (code
      comments, docs, README, commit message) claims "proven", "hardened",
      "100%", "guaranteed", "unbreakable", "military-grade", "enterprise-grade",
      "zero risk" or "production-ready". Every security statement points to a
      measurement — a `file:line` reference, a passing named test
      (`tests/test_*.py::test_*`), or a dated stamp under `docs/`. The rule runs
      in both directions: a check that could not run is an `ERROR`, not a `FAIL`.
      (House rule: `CONTRIBUTING.md` §4 "Ölçülene kadar mühürlenmez"; binding
      code/style rules: `KURALLAR.md`.)
- [ ] Tests were run locally, and the result is written above (including
      failures / skips — a partial run is reported as partial).
- [ ] New or changed tests include a negative control where it makes sense
      (a case that must FAIL, so the test cannot rubber-stamp).
- [ ] Windows-only assumptions are still honoured (PyQt5 tray, DPAPI key,
      WebView2 browser layer); nothing was added that only works elsewhere.
- [ ] No secret, token, vault content or personal data is added to the repo
      (`kasa.toml`, `browser_config.json`, `.vaultkey` stay untracked).
- [ ] Code identifiers may be English, but each touched file carries a Turkish
      explanatory note. Inside code/YAML/TOML the Turkish is ASCII-Turkish (no
      special characters — the Windows console is cp1254 and crashes on them);
      `.md` files may use full Turkish.
- [ ] Only files in scope were changed; unrelated files were left alone.

---

<!-- TR-NOT (ogretici):
Bu depoda en agir hata ABARTMADIR. "Olculene kadar muhurlenmez": bir guvenlik
iddiasi ya bir olcume (dosya:satir veya docs/ altinda tarihli bir belge)
dayanir ya da HIC yazilmaz. Testleri kismen kostuysan bunu kismi olarak bildir;
yesil gorunen ama olcmeyen bir test, kirmiziden daha zararlidir. -->
