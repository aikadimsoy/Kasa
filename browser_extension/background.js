chrome.runtime.onInstalled.addListener(() => {
  console.log("KASA Memory extension installed");
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "PAGE_VISIT") {
    fetch("http://localhost:8000/v1/ingest", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        tool: "event_ingest",
        agent_id: "browser_extension",
        params: {
          source: "chrome_extension",
          type: "page_visit",
          content: request.data,
          ttl_days: 30
        }
      })
    }).catch(err => console.warn("KASA: MCP unreachable", err));
  }
});