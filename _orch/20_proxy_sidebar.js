function renderAg() {
  const panel = document.getElementById('_kasa_panel');
  if (!panel) return;

  panel.innerHTML = '<h2>Ag / Proxy</h2>';

  const div = document.createElement('div');
  div.className = 'kasa-row';
  panel.appendChild(div);

  const checkboxLabel = document.createElement('label');
  checkboxLabel.textContent = 'Proxy kullan';
  div.appendChild(checkboxLabel);

  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.id = '_kasa_proxy_on';
  checkboxLabel.appendChild(checkbox);

  const inputLabel = document.createElement('label');
  inputLabel.textContent = 'Proxy adresi';
  div.appendChild(inputLabel);

  const input = document.createElement('input');
  input.type = 'text';
  input.id = '_kasa_proxy_addr';
  input.placeholder = 'socks5://127.0.0.1:9150';
  inputLabel.appendChild(input);

  const note = document.createElement('div');
  note.textContent = "Değişiklik tarayıcı yeniden başlatılinca geçerli olur. Boş + kapalı = doğrudan bağlantı (gerçek IP).";
  note.style.fontSize = '11px';
  note.style.color = `var(--kasa-n500)`;
  panel.appendChild(note);

  const saveButton = document.createElement('button');
  saveButton.textContent = 'Kaydet';
  saveButton.style.backgroundColor = `var(--kasa-primary)`;
  saveButton.style.color = '#fff';
  div.appendChild(saveButton);

  const torButton = document.createElement('button');
  torButton.textContent = 'Tor (127.0.0.1:9150)';
  div.appendChild(torButton);

  if (typeof window.pywebview !== 'undefined' && typeof window.pywebview.api !== 'undefined') {
    torButton.addEventListener('click', () => {
      input.value = 'socks5://127.0.0.1:9150';
    });

    saveButton.addEventListener('click', () => {
      window.pywebview.api.set_proxy(checkbox.checked, input.value);
    });

    window.pywebview.api.get_proxy().then(cfg => {
      if (typeof cfg === 'object' && cfg !== null) {
        checkbox.checked = cfg.proxy_enabled;
        input.value = cfg.proxy_address || '';
      }
    });
  }
}
