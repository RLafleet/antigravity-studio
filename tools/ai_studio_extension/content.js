// Antigravity AI Studio Bridge Content Script (Trusted Types Immune)
(function () {
  console.log("[Antigravity Bridge] Content script initialized on Google AI Studio!");

  let isExecuting = false;
  const handledTasks = new Set();

  // 1. Create a floating HUD badge without using innerHTML (100% Trusted Types safe)
  const existingBadge = document.getElementById("antigravity-bridge-badge");
  if (existingBadge) existingBadge.remove();

  const badge = document.createElement("div");
  badge.id = "antigravity-bridge-badge";
  badge.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #161b22;
    border: 1px solid #388bfd;
    color: #e6edf3;
    padding: 10px 18px;
    border-radius: 14px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    font-weight: 500;
    z-index: 9999999;
    box-shadow: 0 8px 30px rgba(0,0,0,0.7);
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: default;
    user-select: none;
    backdrop-filter: blur(8px);
  `;

  const dot = document.createElement("span");
  dot.id = "ag-status-dot";
  dot.style.cssText = "width: 10px; height: 10px; border-radius: 50%; background: #2ea043; display: inline-block; box-shadow: 0 0 8px #2ea043;";

  const txt = document.createElement("span");
  txt.id = "ag-status-text";
  txt.textContent = "Antigravity: Подключён к Studio 🟢";

  badge.appendChild(dot);
  badge.appendChild(txt);
  document.body.appendChild(badge);

  function updateStatus(text, color = "#2ea043") {
    const dotEl = document.getElementById("ag-status-dot");
    const txtEl = document.getElementById("ag-status-text");
    if (dotEl) {
      dotEl.style.background = color;
      dotEl.style.boxShadow = `0 0 8px ${color}`;
    }
    if (txtEl) txtEl.textContent = `Antigravity: ${text}`;
  }

  // Bridge communication: uses chrome.runtime (background script) if in extension, or direct fetch
  async function bridgeRequest(action, payload = null) {
    if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
      try {
        const res = await new Promise((resolve) => {
          chrome.runtime.sendMessage({ action, payload }, (response) => {
            if (chrome.runtime.lastError) {
              resolve({ fallback: true });
            } else {
              resolve(response);
            }
          });
        });
        if (res && !res.fallback) {
          if (res.success) return res.data;
          throw new Error(res.error || "Extension bridge error");
        }
      } catch (e) {
        console.warn("[Antigravity Bridge] Extension message failed, falling back to direct fetch:", e);
      }
    }

    // Direct HTTP fetch fallback
    if (action === "poll") {
      const res = await fetch("http://127.0.0.1:48123/api/bridge/poll");
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    }
    if (action === "result") {
      const res = await fetch("http://127.0.0.1:48123/api/bridge/result", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    }
    if (action === "clear") {
      const res = await fetch("http://127.0.0.1:48123/api/bridge/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    }
  }

  // 2. Poll server for pending sprite generation tasks & heartbeat
  async function pollServer() {
    try {
      const data = await bridgeRequest("poll");
      if (!data) return;

      if (!isExecuting) {
        updateStatus("Подключён к Studio 🟢", "#2ea043");
        if (data.task && data.task.id && !handledTasks.has(data.task.id)) {
          handledTasks.add(data.task.id);
          handleTask(data.task);
        }
      }
    } catch (err) {
      if (!isExecuting) {
        updateStatus("Ожидание Studio 🟡", "#d29922");
      }
    }
  }

  // 3. Execute generation task inside AI Studio DOM
  async function handleTask(task) {
    isExecuting = true;
    updateStatus(`Генерация: ${task.id} 🚀`, "#58a6ff");
    console.log("[Antigravity Bridge] Processing task:", task);

    try {
      // Find input field (textarea or contenteditable)
      const selectors = [
        'textarea[placeholder*="Start typing" i]',
        'textarea[placeholder*="prompt" i]',
        'textarea[aria-label*="Type something"]',
        'textarea[placeholder*="Type something"]',
        'textarea.cdk-textarea-autosize',
        'textarea.mat-input-element',
        'ms-autosize-textarea textarea',
        'div[contenteditable="true"]',
        'textarea'
      ];

      let input = null;
      for (const sel of selectors) {
        const elements = document.querySelectorAll(sel);
        for (const el of elements) {
          if (el.offsetParent !== null && !el.disabled) {
            input = el;
            break;
          }
        }
        if (input) break;
      }

      if (!input) {
        throw new Error("Не найдено поле ввода промпта в AI Studio!");
      }

      // Record existing images
      const existingImgs = new Set(
        Array.from(document.querySelectorAll("img")).map((i) => i.src)
      );

      input.focus();

      // Clear existing content & select
      if (input.tagName.toLowerCase() === "textarea") {
        input.select?.();
      }

      // Method 1: document.execCommand('insertText') - native OS keyboard simulation for Angular Form validation
      let execWorked = false;
      try {
        document.execCommand("selectAll", false, null);
        execWorked = document.execCommand("insertText", false, task.prompt);
      } catch (e) {
        execWorked = false;
      }

      // Method 2: Native descriptor setter fallback if execCommand was restricted
      const currentValue = input.value !== undefined ? input.value : input.innerText;
      if (!execWorked || currentValue !== task.prompt) {
        if (input.tagName.toLowerCase() === "textarea") {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
          if (setter) {
            setter.call(input, task.prompt);
          } else {
            input.value = task.prompt;
          }
        } else {
          input.innerText = task.prompt;
        }
      }

      // Method 3: Angular event cascade for Zone.js and ControlValueAccessor
      input.dispatchEvent(new Event("focus", { bubbles: true }));
      try {
        input.dispatchEvent(new InputEvent("beforeinput", {
          bubbles: true,
          cancelable: true,
          inputType: "insertText",
          data: task.prompt
        }));
        input.dispatchEvent(new InputEvent("input", {
          bubbles: true,
          composed: true,
          inputType: "insertText",
          data: task.prompt
        }));
      } catch (e) {
        input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
      }
      input.dispatchEvent(new Event("change", { bubbles: true, composed: true }));

      // Give Angular change detection time to validate input and update button state
      await new Promise((r) => setTimeout(r, 450));

      // Find Run button (Google AI Studio uses "Run Ctrl ↵" or aria-label="Run")
      function findRunButton() {
        const allButtons = Array.from(document.querySelectorAll("button"));
        return allButtons.find((b) => {
          const text = (b.textContent || "").trim().toLowerCase();
          const aria = (b.getAttribute("aria-label") || "").toLowerCase();
          const testId = (b.getAttribute("data-test-id") || "").toLowerCase();
          return (
            text.startsWith("run") ||
            text.includes("run") ||
            aria === "run" ||
            aria.includes("run") ||
            testId.includes("run")
          );
        });
      }

      let runBtn = findRunButton();

      // Wait up to 3 seconds for Angular to enable the button if it's currently disabled
      for (let attempt = 0; attempt < 30; attempt++) {
        if (runBtn && !runBtn.disabled && runBtn.getAttribute("aria-disabled") !== "true") {
          break;
        }
        await new Promise((r) => setTimeout(r, 100));
        runBtn = findRunButton();
      }

      // Trigger button with full pointer & mouse sequence
      if (runBtn) {
        runBtn.removeAttribute("disabled");
        runBtn.setAttribute("aria-disabled", "false");
        ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
          runBtn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
        });
        runBtn.click();
      }

      // Also dispatch Ctrl+Enter on both input and window
      ["keydown", "keypress", "keyup"].forEach((type) => {
        const enterEvt = new KeyboardEvent(type, {
          key: "Enter",
          code: "Enter",
          keyCode: 13,
          which: 13,
          ctrlKey: true,
          metaKey: true,
          bubbles: true,
          cancelable: true,
          composed: true
        });
        input.dispatchEvent(enterEvt);
        window.dispatchEvent(enterEvt);
      });

      updateStatus("Ожидание картинки от Nano Banana... ⏳", "#58a6ff");

      // Wait for output image
      const targetImg = await waitForNewImage(existingImgs, 120);

      if (!targetImg) {
        throw new Error("Таймаут генерации изображения (120 сек)");
      }

      updateStatus("Скачивание спрайта... 📦", "#a371f7");

      // Convert image to Base64
      const b64 = await imageToBase64(targetImg);

      // Submit result to Antigravity Studio
      await bridgeRequest("result", {
        task_id: task.id,
        image_base64: b64,
      });

      updateStatus("Спрайт готов и нарезан! 🎉", "#2ea043");
      console.log("[Antigravity Bridge] Task completed successfully!");
    } catch (err) {
      console.error("[Antigravity Bridge] Error:", err);
      updateStatus(`Ошибка: ${err.message} ❌`, "#f85149");
      try {
        await bridgeRequest("clear");
      } catch (e) {}
    } finally {
      setTimeout(() => {
        isExecuting = false;
      }, 5000);
    }
  }

  function waitForNewImage(existingImgs, timeoutSeconds = 120) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const interval = setInterval(() => {
        if (Date.now() - startTime > timeoutSeconds * 1000) {
          clearInterval(interval);
          resolve(null);
          return;
        }

        // 1. Check for AI Studio Safety / Content Policy violations
        const bodyText = document.body.innerText || "";
        if (bodyText.includes("Prohibited content") || bodyText.includes("Safety policy violation")) {
          clearInterval(interval);
          reject(new Error("AI Studio отклонил промпт (Prohibited content)"));
          return;
        }

        // 2. Check for real output image with authentic bitmap dimensions (never UI thumbnails)
        const imgs = document.querySelectorAll("img");
        for (const img of imgs) {
          if (!existingImgs.has(img.src) && img.src && !img.src.includes("data:image/svg")) {
            const isAvatar = /avatar|profile|icon|favicon|logo|gallery/i.test(img.src) || /avatar|profile|icon|favicon|logo|gallery/i.test(img.className);
            const natW = img.naturalWidth || 0;
            const natH = img.naturalHeight || 0;

            // Must be genuine loaded output sprite (at least 300x300 real pixels)
            if (!isAvatar && img.complete && natW >= 300 && natH >= 300) {
              clearInterval(interval);
              resolve(img);
              return;
            }
          }
        }
      }, 1500);
    });
  }

  async function imageToBase64(img) {
    // Ensure image is fully loaded
    if (!img.complete || img.naturalWidth === 0) {
      await new Promise((r) => {
        img.onload = r;
        setTimeout(r, 2000);
      });
    }

    try {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth || img.width || 800;
      canvas.height = img.naturalHeight || img.height || 600;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      return canvas.toDataURL("image/png");
    } catch (e) {
      const resp = await fetch(img.src);
      const blob = await resp.blob();
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    }
  }

  // --- ANTI-THROTTLE BACKGROUND ENGINE ---
  // Web Workers run in an isolated thread and are NOT throttled to 1min by Chromium/Edge
  let workerStarted = false;
  try {
    const workerBlob = new Blob([`
      setInterval(() => { postMessage('tick'); }, 1500);
    `], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(workerBlob);
    const bgWorker = new Worker(workerUrl);
    bgWorker.onmessage = () => {
      pollServer();
    };
    workerStarted = true;
    console.log("[Antigravity Bridge] Anti-throttle Web Worker active! Background polling is unthrottled.");
  } catch (err) {
    console.warn("[Antigravity Bridge] Web Worker unavailable, using window.setInterval:", err);
  }

  // Unconditional Interval (always active, immune to worker CSP blocking)
  setInterval(pollServer, 1500);

  // Wakeup immediately when user focuses the tab
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      console.log("[Antigravity Bridge] Tab focused, triggering immediate poll...");
      pollServer();
    }
  });

  // Anti-Sleep Audio Keepalive (Makes Chromium treat tab as background media player - NEVER throttled)
  let keepaliveActive = false;
  function initAudioKeepalive() {
    if (keepaliveActive) return;
    try {
      // 1. Silent HTML5 Audio Element (44-byte silent WAV data URI)
      const silentWav = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
      const audio = new Audio(silentWav);
      audio.loop = true;
      audio.volume = 0.001; // Virtually inaudible
      audio.play().then(() => {
        keepaliveActive = true;
        console.log("[Antigravity Bridge] Silent audio keepalive running! Edge will NEVER sleep this tab even when minimized.");
      }).catch(() => {});

      // 2. Fallback WebAudio Oscillator
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const actx = new AudioCtx();
        if (actx.state === "suspended") {
          actx.resume();
        }
        const osc = actx.createOscillator();
        const gain = actx.createGain();
        gain.gain.value = 0.00001;
        osc.connect(gain);
        gain.connect(actx.destination);
        osc.start();
        keepaliveActive = true;
      }
    } catch (e) {}
  }

  // Trigger on ANY first user interaction anywhere on screen
  ["click", "keydown", "pointerdown", "focus"].forEach((evt) => {
    window.addEventListener(evt, initAudioKeepalive, { once: true });
  });

  // Also trigger when clicking the floating badge
  badge.addEventListener("click", () => {
    initAudioKeepalive();
    updateStatus("Подключён к Studio 🟢 (Анти-сон ВКЛ)");
  });

  // Initial immediate poll
  pollServer();
})();
