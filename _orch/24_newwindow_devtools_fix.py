def open_browser(url="https://lite.duckduckgo.com/lite"):
    _apply_proxy_env()
    api = KasaApi()
    win = webview.create_window("KASA Browser", url, js_api=api, width=1280, height=860)
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False  # Dış bağlantıların dış tarayıcıda açılmasını engelle
    webview.start(debug=True)  # Geliştirici araçlarını etkinleştirerek hata ayıklama yapabilmek için debug modunu aktifleştir
