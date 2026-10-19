// Antigravity AI Studio Bridge - Background Service Worker (Manifest V3)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "poll") {
    fetch("http://127.0.0.1:48123/api/bridge/poll")
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (request.action === "result") {
    fetch("http://127.0.0.1:48123/api/bridge/result", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (request.action === "clear") {
    fetch("http://127.0.0.1:48123/api/bridge/clear", {
      method: "POST",
    })
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});
