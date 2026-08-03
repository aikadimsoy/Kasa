# -*- coding: utf-8 -*-
"""
NAMED-PIPE SUREC-KIMLIGI SPIKE — v2 fizibilite olcumu (gercek Windows API).

SORU: KASA yerel-tek-makine. Kimligi PAYLASILAN BIR SIR (bearer token) yerine, baglanan
    surecin OS kimligine baglayabilir miyiz? Boylece token hirsizligi/F-IMP/A6 kokten kapanir
    (ortada calinacak sir yok; kimligi KERNEL soyler).

NE OLCER: bir named pipe kurar, bir istemci baglanir, sunucu GetNamedPipeClientProcessId ile
    baglanan surecin PID'ini KERNEL'den alir, sonra o PID'den surec YOLUNU cozer. Paylasilan
    sir KULLANILMAZ. Bu, "OS surec kimligi ile bind" yaklasiminin Windows tesisatinin
    calistigini kanitlar (taahhutten once olc).

SINIR (dürüst): istemci ile sunucu bu spike'ta AYNI surectedir (thread) -> raporlanan istemci
    PID = kendi PID'imiz; bu, API'nin DOGRU baglanan surecin PID'ini verdigini kanitlamak icin
    yeterlidir. Gercek dagitimda istemci AYRI bir surectir ve onun PID'i raporlanir. Ayrica bu
    da CANLI ele gecirmeyi durdurmaz (mesru surece sizan kod onun kimligini tasir) — ama
    dinleme/replay/token-hirsizligi/F-IMP'i sirsiz kapatir.
"""
import os
import sys
import threading
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import win32pipe
    import win32file
    import win32api
    import win32process
    import win32con
    import pywintypes
except Exception as e:  # pragma: no cover
    print("pywin32 yok/yuklenemedi:", e)
    raise SystemExit(1)

PIPE_NAME = r"\\.\pipe\kasa_identity_spike"


def _client_pid_of(handle):
    """Baglanan istemci surecinin PID'ini KERNEL'den al. win32pipe'ta varsa onu kullan;
    yoksa dogrudan kernel32.GetNamedPipeClientProcessId'a ctypes ile dus."""
    fn = getattr(win32pipe, "GetNamedPipeClientProcessId", None)
    if fn is not None:
        return fn(handle)
    import ctypes
    from ctypes import wintypes
    pid = wintypes.DWORD(0)
    raw = int(handle)  # PyHANDLE -> ham HANDLE
    ok = ctypes.windll.kernel32.GetNamedPipeClientProcessId(wintypes.HANDLE(raw), ctypes.byref(pid))
    if not ok:
        raise OSError("GetNamedPipeClientProcessId basarisiz")
    return pid.value


def _image_path_of(pid):
    """PID'den surecin tam imaj yolunu coz (imza/dogrulama buraya eklenir). Alinamazsa mesaj."""
    try:
        h = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        try:
            return win32process.GetModuleFileNameEx(h, 0)
        finally:
            win32api.CloseHandle(h)
    except Exception as e:
        return f"(yol cozulemedi: {e})"


def server(result):
    """Named pipe'i kurar, tek istemci bekler, kernel-onayli kimligi okur."""
    handle = win32pipe.CreateNamedPipe(
        PIPE_NAME,
        win32pipe.PIPE_ACCESS_DUPLEX,
        win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT,
        1, 4096, 4096, 0, None)
    try:
        win32pipe.ConnectNamedPipe(handle, None)
        # KERNEL-ONAYLI: baglanan istemcinin PID'i (istemci HICBIR sir sunmadi).
        pid = _client_pid_of(handle)
        result["pid"] = pid
        result["path"] = _image_path_of(pid)
    except Exception as e:
        result["error"] = repr(e)
    finally:
        win32file.CloseHandle(handle)


def client():
    """Sirf baglanir (kimlik dogrulamasi icin hicbir sir/gonderim gerekmez)."""
    time.sleep(0.3)
    for _ in range(40):
        try:
            h = win32file.CreateFile(
                PIPE_NAME, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None,
                win32file.OPEN_EXISTING, 0, None)
            win32file.CloseHandle(h)
            return
        except pywintypes.error:
            time.sleep(0.1)


def run():
    print("\n=== NAMED-PIPE SUREC-KIMLIGI SPIKE ===\n")
    result = {}
    t = threading.Thread(target=server, args=(result,), daemon=True)
    t.start()
    client()
    t.join(timeout=5)

    my_pid = os.getpid()
    if "error" in result:
        print("  HATA:", result["error"])
        return 1
    pid = result.get("pid")
    print(f"  kernel'in bildirdigi istemci PID : {pid}")
    print(f"  bu surecin PID'i (os.getpid)     : {my_pid}")
    print(f"  cozulen surec yolu               : {result.get('path')}")
    match = (pid == my_pid)
    print(f"\n  API dogru baglanan sureci verdi mi: {'EVET' if match else 'HAYIR'}")
    print("\n=== DURUST OKUMA ===")
    print("  * Kimlik PAYLASILAN SIR olmadan, KERNEL'den geldi -> token hirsizligi/F-IMP/A6")
    print("    bu yaklasimda kokten kapanir (ortada calinacak/taklit edilecek sir yok).")
    print("  * Ayni surecte PID kendi PID'imize esit cikmasi API'nin dogru calistiginin kanitidir;")
    print("    gercek dagitimda istemci ayri surectir ve onun kimligi/imza-yolu dogrulanir.")
    print("  * SINIR: bu da CANLI ele gecirmeyi durdurmaz (mesru surece sizan kod onun kimligini")
    print("    tasir) -> savunmanin tavani yine mimari (uc salt-okunur arac).")
    print("  FIZIBILITE: Windows tesisati CALISIYOR -> v2 icin gercekci bir yol.\n")
    return 0 if match else 2


if __name__ == "__main__":
    raise SystemExit(run())
