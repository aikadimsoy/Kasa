def _register_early_privacy(win):
    """CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync ile _PRIVACY_JS'i
    sayfa scriptlerinden ONCE calistir. Tum sonraki navigasyonlarda gecerli.
    Basari/hata durumunu bool doner."""
    try:
        from webview.platforms.winforms import BrowserView
        from System import Action
        
        instance = BrowserView.instances.get(win.uid)
        if instance is None:
            return False
        
        def inner():
            core = instance.browser.webview.CoreWebView2
            if core is None:
                return
            try:
                core.AddScriptToExecuteOnDocumentCreatedAsync(_PRIVACY_JS)
            except Exception as e:
                print(f"[KASA] erken enjeksiyon: {e}")
        
        instance.BeginInvoke(Action(inner))
        return True
    except Exception as e:
        print(f"[KASA] erken enjeksiyon: {e}")
        return False
