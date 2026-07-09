# -*- coding: utf-8 -*-
"""WebGL2 baglaminda da GPU spoof uygulanmis olmali (WebGL1-only patch sizinti birakiyordu)."""
import os

BROWSER_FILE = os.path.join("d:/kasa", "src/browser/browser_window.py")


def _read():
    with open(BROWSER_FILE, encoding="utf-8") as f:
        return f.read()


def test_webgl2_context_patched():
    src = _read()
    assert "WebGL2RenderingContext" in src, "WebGL2 baglami hic yamanmamis, GPU sizmaya devam eder"


def test_webgl2_patch_near_poisoning_block_and_reuses_seed():
    src = _read()
    start = src.find("WebGL Fingerprint Poisoning")
    assert start != -1, "WebGL Fingerprint Poisoning bolumu bulunamadi"
    end = src.find("Known Tracker Cookie Poisoning")
    assert end != -1 and end > start
    block = src[start:end]
    assert "WebGL2RenderingContext" in block, "WebGL2 yamasi dogru bolumde degil"
    assert block.count("_kp_webgl_idx") >= 2, (
        "WebGL2 patch'i WebGL1 ile AYNI seed'i (_kp_webgl_idx) kullanmali "
        "(aksi halde iki baglam farkli sahte deger doner, bu tutarsizlik "
        "kendisi yeni bir teshis sinyali olur)"
    )


def test_webgl1_patch_still_present():
    src = _read()
    assert "webglProto.getParameter" in src
    assert "WebGLRenderingContext.prototype" in src
