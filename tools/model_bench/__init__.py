# kasa/tools/model_bench/__init__.py

"""
Model olcum tezgahi (F0) — bir yerel model adayinin KASA rolune uygunlugunu OLCER.

Turkce not: bu paket hicbir sey duzeltmez, yalniz olcer ve damga basar
(docs/adr/0002 ile ayni ilke: benchmark olcer, duzeltme sahip kararidir).
Amac, "hangi model" sorusunu tahminle degil kanitla cevaplamak — repo kurali
"muhur = olcum". Tezgah calisma-zamani kodunu (gate.py / harness.py) DEGISTIRMEZ,
tam tersine ONLARI kullanarak olcer: boylece olculen sey uretimdeki davranistir.
"""
