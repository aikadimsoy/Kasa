(function() {
  if (!location.protocol.startsWith('http')) return;

  const summary = document.body.innerText.slice(0, 500).replace(/\s+/g, ' ').trim();
  chrome.runtime.sendMessage({
    type: "PAGE_VISIT",
    data: { url: location.href, title: document.title, summary }
  });
})();