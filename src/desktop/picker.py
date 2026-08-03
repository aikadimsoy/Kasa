# kasa/src/desktop/picker.py

"""
Native dosya/klasor secici — pywebview js_api koprusu.

JS tarafi `window.pywebview.api.pick_folder()/pick_file()` cagirir; secilen yol string olarak
doner ve %APPDATA%/KASA/settings.json'a kaydedilir (sonraki acilista vault yolu olarak kullanilir,
bkz. launch.py:_prepare_env). Air-gap: yalniz native OS diyalogu, harici bagimlilik yok.

KARARLILIK NOTU: window nesnesini bu API'de ONITELIK olarak SAKLAMA. pywebview js_api nesnesini
JS'e acarken oznitelikleri serialize eder; .window ozniteligi WebView2 native COM nesnesini
ozyinelemeli tarar -> introspection firtinasi + recursion + pencere kararsizligi. Cozum: pencereye
metod icinde `webview.active_window()` ile LAZY eris (api grafinde window referansi tutma).
"""

import json
import pathlib

import webview


class PickerApi:
    def __init__(self, data_dir):
        self.data_dir = data_dir      # kalici veri dizini (pathlib.Path). window SAKLANMAZ.

    def _dialog(self, dialog_type) -> str:
        """Aktif pencere uzerinden native diyalogu ac; secilen yolu doner (iptal/hata -> '')."""
        try:
            win = webview.active_window()
            if win is None:
                return ""
            result = win.create_file_dialog(dialog_type)
            if isinstance(result, (list, tuple)) and len(result) > 0:
                return str(result[0])
            return ""
        except Exception as e:
            print(f"Error in file dialog: {e}")
            return ""

    def pick_folder(self) -> str:
        path = self._dialog(webview.FOLDER_DIALOG)
        if path:
            self._save(path)
        return path

    def pick_file(self) -> str:
        path = self._dialog(webview.OPEN_DIALOG)
        if path:
            self._save(path)
        return path

    def _save(self, path):
        """Secilen yolu settings.json'a DIZIN olarak yazar (utf-8).

        SEBEP: vault_path bir DIZIN olmak zorunda — Vault.__init__ once os.makedirs(vault_path)
        cagirir, sonra icine kasa.db acar. "Dosya Bul" butonu dosya yolu donduruyordu ve burasi
        onu oldugu gibi vault_path'e yaziyordu.
        SONUC (fixlenmezse): sonraki acilista os.makedirs(dosya_yolu) -> FileExistsError, ve bu
        launch.py'nin MODUL-seviyesi import'unda patliyor -> main() hic calismiyor -> _preflight_gate
        mesaj kutusu bile cikmiyor. Konsolsuz exe'de uygulama SESSIZCE acilmiyor.
        KARAR: dosya secilirse kullanicinin niyeti "vault bu dosyanin yaninda" demektir ->
        parent dizini kaydedilir. Klasor secimi zaten dizindir, degismez."""
        try:
            p = pathlib.Path(path)
            if p.is_file():
                p = p.parent
            settings_path = self.data_dir / "settings.json"
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump({"vault_path": str(p)}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving vault path: {e}")

    def get_saved_vault_path(self) -> str:
        """Kayitli vault yolunu doner; yoksa/hata -> ''. """
        try:
            settings_path = self.data_dir / "settings.json"
            if settings_path.is_file():
                with open(settings_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("vault_path", "")
            return ""
        except Exception as e:
            print(f"Error reading vault path: {e}")
            return ""
