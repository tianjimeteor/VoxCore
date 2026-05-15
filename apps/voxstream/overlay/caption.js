// VoxStream overlay — connect to /ws/caption and render lines.
//
// URL params:
//   theme       streaming | classroom | meeting | minimal
//   max_lines   how many lines to keep on screen (default 3)
//   linger      ms a finalized line stays before fading (default 6000)
//   debug       set to "1" to render demo lines without a server.
(function () {
  "use strict";

  const params = new URLSearchParams(location.search);
  const theme = params.get("theme") || "streaming";
  const maxLines = clampInt(params.get("max_lines"), 1, 12, 3);
  const linger = clampInt(params.get("linger"), 1000, 60000, 6000);
  const debug = params.get("debug") === "1";

  // Detect OBS Browser Source so we can hide the hint card.
  if (navigator.userAgent && navigator.userAgent.toLowerCase().includes("obs/")) {
    document.body.classList.add("in-obs");
  }
  document.body.className = "theme-" + theme + (document.body.classList.contains("in-obs") ? " in-obs" : "");

  const $captions = document.getElementById("captions");
  const $status = document.getElementById("status");
  const $hintUrl = document.getElementById("hint-url");
  if ($hintUrl) $hintUrl.textContent = location.origin + location.pathname + location.search;

  // ---- Caption rendering ---------------------------------------------------

  let partialEl = null;

  function pushLine(payload) {
    const text = (payload && payload.text) || "";
    if (!text.trim()) return;

    const isFinal = !!payload.final;
    const translated = !!payload.translated;

    if (!isFinal) {
      if (!partialEl) {
        partialEl = document.createElement("div");
        partialEl.className = "line partial";
        $captions.appendChild(partialEl);
      }
      partialEl.textContent = text;
      pruneLines();
      return;
    }

    // Finalize: convert partial in place, or append new.
    let el = partialEl;
    partialEl = null;
    if (!el) {
      el = document.createElement("div");
      $captions.appendChild(el);
    }
    el.className = "line final" + (translated ? " translated" : "");
    el.textContent = text;
    pruneLines();
    setTimeout(() => fadeOut(el), linger);
  }

  function pruneLines() {
    const lines = $captions.querySelectorAll(".line");
    if (lines.length <= maxLines) return;
    for (let i = 0; i < lines.length - maxLines; i++) {
      fadeOut(lines[i]);
    }
  }

  function fadeOut(el) {
    if (!el || el.classList.contains("fadeout")) return;
    el.classList.add("fadeout");
    setTimeout(() => { try { el.remove(); } catch (_) {} }, 380);
  }

  // ---- WebSocket -----------------------------------------------------------

  function setStatus(cls) {
    $status.classList.remove("status--connecting", "status--ok", "status--error");
    $status.classList.add("status--" + cls);
  }

  let ws = null;
  let reconnectTimer = null;
  function connect() {
    setStatus("connecting");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = proto + "://" + location.host + "/ws/caption";
    try {
      ws = new WebSocket(url);
    } catch (err) {
      console.error("[voxstream] ws ctor failed", err);
      scheduleReconnect();
      return;
    }
    ws.onopen = () => setStatus("ok");
    ws.onclose = () => { setStatus("error"); scheduleReconnect(); };
    ws.onerror = () => { setStatus("error"); };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        pushLine(data);
      } catch (err) {
        console.error("[voxstream] bad json from server", err, ev.data);
      }
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, 1500);
  }

  // ---- Helpers -------------------------------------------------------------

  function clampInt(raw, min, max, fallback) {
    const n = parseInt(raw, 10);
    if (isNaN(n)) return fallback;
    return Math.max(min, Math.min(max, n));
  }

  // ---- Boot ---------------------------------------------------------------

  if (debug) {
    setStatus("ok");
    const samples = [
      { text: "Hello and welcome to the stream.", final: true },
      { text: "Powered by VoxCore — open-source real-time voice AI.", final: true },
      { text: "Add this page as an OBS Browser Source for free captions.", final: true },
      { text: "由 VoxCore 提供实时字幕支持。", final: true, translated: true },
    ];
    let i = 0;
    setInterval(() => pushLine(samples[i++ % samples.length]), 2200);
    return;
  }

  connect();
})();
