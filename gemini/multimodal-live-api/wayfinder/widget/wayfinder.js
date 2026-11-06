// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Wayfinder — Navigation copilot for complex UIs.
// Embeddable AI assistant widget. Drop this script on any page.
//
// Dual transport:
//   - default text mode: POST /v1/chat/stream, SSE response
//   - voice mode (mic toggle): WebSocket /ws to Gemini Live API
// Tool calls for DOM actions are handled identically in both modes.

(function () {
  "use strict";

  // ---- Backend origin (same origin as the script) ----
  var scriptEl =
    document.currentScript ||
    document.querySelector('script[src*="wayfinder.js"]');
  var BACKEND_ORIGIN = scriptEl
    ? new URL(scriptEl.src).origin
    : window.location.origin;
  var WS_URL = BACKEND_ORIGIN.replace(/^http/, "ws") + "/ws";
  var CHAT_URL = BACKEND_ORIGIN + "/v1/chat/stream";
  var TOOL_RESULT_URL = BACKEND_ORIGIN + "/v1/chat/tool_result";
  var API_KEY = scriptEl ? scriptEl.getAttribute("data-key") : null;
  // Optional logical grounding/tenant key. Lets pages on the SAME host
  // (e.g. localhost) route to different knowledge bases. Auth still uses
  // the real page origin; this only selects the RAG pipeline.
  var TENANT = scriptEl ? scriptEl.getAttribute("data-tenant") : null;

  // ---- State ----
  var transport = "text"; // "text" or "voice"
  var ws = null;
  var wsConnected = false;
  var panelOpen = false;
  var sendingFrame = false;
  var sessionId = null;
  var streaming = false;

  // Voice tuning. data-barge-in="false" mutes the mic while the model speaks.
  var BARGE_IN =
    !scriptEl || scriptEl.getAttribute("data-barge-in") !== "false";
  var FRAME_INTERVAL_MS = 3000; // periodic screen frames while the mic is on
  var PAGE_STATE_DELAY_MS = 400; // settle time after actions before re-scanning
  var TOOL_RESULT_DELAY_MS = 250; // let the page react before reporting results
  var frameTimer = null;

  // Audio state (voice mode only)
  var mediaStream = null;
  var audioContext = null;
  var recording = false;
  var playbackCtx = null;
  var audioQueue = [];
  var currentSource = null;
  var isPlaying = false;
  var micCooldown = false;

  // Chat transcript
  var pendingAssistantEl = null;
  var pendingUserEl = null;

  // ---- Shadow DOM Setup ----
  var hostDiv = document.createElement("div");
  hostDiv.id = "wayfinder-root";
  document.body.appendChild(hostDiv);
  var shadow = hostDiv.attachShadow({ mode: "open" });

  var style = document.createElement("style");
  style.textContent = WIDGET_CSS();
  shadow.appendChild(style);

  // Load html2canvas (used by voice mode for screen frames). Self-hosted by
  // the Wayfinder backend so host pages don't pull code from a public CDN.
  if (typeof html2canvas === "undefined") {
    var h2cScript = document.createElement("script");
    h2cScript.src = BACKEND_ORIGIN + "/vendor/html2canvas.min.js";
    document.head.appendChild(h2cScript);
  }

  var container = document.createElement("div");
  container.className = "wf-container";
  container.innerHTML = FAB_HTML() + PANEL_HTML();
  shadow.appendChild(container);

  // ---- DOM Refs (inside shadow) ----
  var fab = shadow.querySelector(".wf-fab");
  var panel = shadow.querySelector(".wf-panel");
  var closeBtn = shadow.querySelector(".wf-close-btn");
  var chatMessages = shadow.querySelector(".wf-messages");
  var chatInput = shadow.querySelector(".wf-input");
  var chatSend = shadow.querySelector(".wf-send-btn");
  var micBtn = shadow.querySelector(".wf-mic-btn");
  var connectionDot = shadow.querySelector(".wf-dot");
  var connectionText = shadow.querySelector(".wf-status-text");
  var modeLabel = shadow.querySelector(".wf-mode-label");

  // ---- FAB / Panel ----
  fab.addEventListener("click", function () {
    panelOpen = !panelOpen;
    panel.classList.toggle("open", panelOpen);
    fab.classList.toggle("hidden", panelOpen);
    if (panelOpen) {
      setTransportUi("text");
      setConnectionStatus("ready");
      chatSend.disabled = false;
    }
  });

  closeBtn.addEventListener("click", function () {
    panelOpen = false;
    panel.classList.remove("open");
    fab.classList.remove("hidden");
  });

  // Demo convenience: ?wf_prompt=... opens the panel with the prompt typed
  // in (never auto-sent), so the persona page can hand off a sample request.
  try {
    var presetPrompt = new URLSearchParams(window.location.search).get(
      "wf_prompt",
    );
    if (presetPrompt) {
      setTimeout(function () {
        if (!panelOpen) fab.click();
        chatInput.value = presetPrompt.slice(0, 500);
        chatInput.focus();
      }, 300);
    }
  } catch {
    /* URLSearchParams unsupported: ignore */
  }

  // ==================================================
  // Text transport (default): POST /v1/chat/stream + SSE
  // ==================================================
  async function sendTextTurn(message) {
    if (streaming) return;
    streaming = true;
    chatSend.disabled = true;

    addMessage("user", message);

    var manifest = scanPageElements();
    var body = {
      session_id: sessionId,
      origin: window.location.hostname,
      tenant: TENANT,
      api_key: API_KEY,
      message: message,
      page_manifest: manifest,
    };

    try {
      var resp = await fetch(CHAT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        var errText = await resp.text();
        addMessage("error", "Chat failed: " + resp.status + " " + errText);
        return;
      }

      await readSseStream(resp);
    } catch (err) {
      addMessage("error", "Network error: " + err.message);
    } finally {
      streaming = false;
      chatSend.disabled = false;
      pendingAssistantEl = null;
    }
  }

  async function readSseStream(response) {
    var reader = response.body.getReader();
    var decoder = new TextDecoder("utf-8");
    var buffer = "";

    while (true) {
      var chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });

      // Events end with a blank line; accept \n and \r\n line endings.
      var events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop(); // keep last (possibly incomplete) event
      for (var i = 0; i < events.length; i++) {
        handleSseEvent(events[i]);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) handleSseEvent(buffer); // stream ended without a trailing blank line
  }

  function handleSseEvent(raw) {
    var event = "message";
    var dataLines = [];
    var lines = raw.split(/\r?\n/);
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.indexOf("event:") === 0) {
        event = line.slice(6).trim();
      } else if (line.indexOf("data:") === 0) {
        // Per the SSE spec, strip one optional leading space and keep
        // newlines between data lines (multi-line answers).
        var value = line.slice(5);
        if (value.charAt(0) === " ") value = value.slice(1);
        dataLines.push(value);
      }
    }
    var data = dataLines.join("\n");
    if (!dataLines.length) return;

    switch (event) {
      case "session":
        try {
          var sMeta = JSON.parse(data);
          if (sMeta.session_id) sessionId = sMeta.session_id;
        } catch {
          /* ignore */
        }
        break;
      case "text":
        appendAssistantText(data);
        break;
      case "tool_call":
        try {
          var call = JSON.parse(data);
          handleToolCalls([
            { id: call.id, name: call.name, args: call.args || {} },
          ]);
        } catch (e) {
          console.error("Bad tool_call payload:", e);
        }
        break;
      case "done":
        try {
          var meta = JSON.parse(data);
          if (meta.session_id) sessionId = meta.session_id;
        } catch {
          /* ignore */
        }
        finalizeTurn();
        break;
      case "error":
        try {
          var err = JSON.parse(data);
          addMessage("error", err.error || "Unknown error");
        } catch {
          addMessage("error", data);
        }
        break;
    }
  }

  // ==================================================
  // Voice transport (opt-in): WebSocket to Live API
  // ==================================================
  var reconnectTimer = null;

  function connectWebSocket(onReady) {
    if (
      ws &&
      (ws.readyState === WebSocket.CONNECTING ||
        ws.readyState === WebSocket.OPEN)
    ) {
      if (onReady) onReady();
      return;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    setConnectionStatus("connecting");
    ws = new WebSocket(WS_URL);

    ws.onopen = function () {
      wsConnected = true;
      setConnectionStatus("connected");

      var initMsg = {
        type: "init",
        origin: window.location.hostname,
        url: window.location.href,
        title: document.title,
      };
      if (TENANT) initMsg.tenant = TENANT;
      if (API_KEY) initMsg.api_key = API_KEY;
      safeSend(JSON.stringify(initMsg));

      var manifest = scanPageElements();
      safeSend(JSON.stringify({ type: "page_manifest", elements: manifest }));

      if (onReady) onReady();
    };

    ws.onmessage = function (event) {
      handleWsMessage(JSON.parse(event.data));
    };

    ws.onclose = function () {
      wsConnected = false;
      stopRecording();
      if (transport === "voice") {
        setConnectionStatus("disconnected");
        reconnectTimer = setTimeout(function () {
          connectWebSocket();
        }, 5000);
      }
    };

    ws.onerror = function () {};
  }

  function setConnectionStatus(status) {
    connectionDot.className = "wf-dot " + status;
    var labels = {
      connected: "Voice connected",
      connecting: "Connecting...",
      disconnected: "Disconnected",
      ready: "Ready",
    };
    connectionText.textContent = labels[status] || status;
  }

  function setTransportUi(t) {
    transport = t;
    micBtn.classList.toggle("active", t === "voice");
    modeLabel.textContent = t === "voice" ? "Voice" : "Text";
    modeLabel.className = "wf-mode-label " + (t === "voice" ? "voice" : "text");
  }

  function safeSend(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(data);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }

  function handleWsMessage(msg) {
    switch (msg.type) {
      case "ready":
        // mode is informational; transport stays "voice" while this socket is open
        window.postMessage({ type: "wayfinder:ready", mode: msg.mode }, "*");
        break;
      case "text":
        appendAssistantText(msg.text);
        break;
      case "audio":
        playAudioChunk(msg.data, msg.mime_type);
        break;
      case "turn_complete":
        finalizeTurn();
        break;
      case "tool_call":
        handleToolCalls(msg.calls);
        break;
      case "interrupted":
        handleInterrupted();
        break;
      case "input_transcript":
        appendUserTranscript();
        break;
      case "output_transcript":
        appendAssistantText(msg.text);
        break;
      case "error":
        addMessage("error", msg.error);
        if (msg.code === "AUTH_FAILED") {
          if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
          }
          setConnectionStatus("disconnected");
          connectionText.textContent = "Auth Failed";
        }
        break;
    }
  }

  function handleInterrupted() {
    // Barge-in: drop queued audio and stop what is playing right now.
    audioQueue = [];
    if (currentSource) {
      try {
        currentSource.onended = null;
        currentSource.stop();
      } catch {
        /* already stopped */
      }
      currentSource = null;
    }
    isPlaying = false;
    pendingAssistantEl = null;
    pendingUserEl = null;
  }

  // ---- Transcript helpers ----
  function appendUserTranscript() {
    if (!pendingUserEl) {
      pendingUserEl = document.createElement("div");
      pendingUserEl.className = "wf-msg user";
      pendingUserEl.textContent = "You: ...";
      chatMessages.appendChild(pendingUserEl);
      scrollChat();
    }
  }

  function appendAssistantText(text) {
    if (!pendingAssistantEl) {
      pendingAssistantEl = document.createElement("div");
      pendingAssistantEl.className = "wf-msg assistant";
      pendingAssistantEl.textContent = "";
      chatMessages.appendChild(pendingAssistantEl);
    }
    pendingAssistantEl.textContent += text;
    scrollChat();
  }

  function finalizeTurn() {
    pendingAssistantEl = null;
    pendingUserEl = null;
    if (transport === "voice" && !isPlaying) {
      micCooldown = true;
      setTimeout(function () {
        micCooldown = false;
      }, 1500);
    }
  }

  // ==================================================
  // Audio playback (voice mode)
  // ==================================================
  function getPlaybackContext() {
    if (!playbackCtx) playbackCtx = new AudioContext({ sampleRate: 24000 });
    return playbackCtx;
  }

  function ensurePlaybackReady() {
    var ctx = getPlaybackContext();
    if (ctx.state === "suspended") ctx.resume();
  }

  function playAudioChunk(base64Data) {
    var raw = atob(base64Data);
    var bytes = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

    var ctx = getPlaybackContext();
    var samples = new Int16Array(bytes.buffer);
    var floats = new Float32Array(samples.length);
    for (var j = 0; j < samples.length; j++) floats[j] = samples[j] / 32768;

    var buffer = ctx.createBuffer(1, floats.length, 24000);
    buffer.getChannelData(0).set(floats);
    audioQueue.push(buffer);
    if (!isPlaying) drainAudioQueue();
  }

  function drainAudioQueue() {
    if (audioQueue.length === 0) {
      isPlaying = false;
      micCooldown = true;
      setTimeout(function () {
        micCooldown = false;
      }, 1500);
      return;
    }
    isPlaying = true;
    var ctx = getPlaybackContext();
    var buffer = audioQueue.shift();
    var source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = drainAudioQueue;
    currentSource = source;
    source.start();
  }

  // ==================================================
  // Microphone (voice mode)
  // ==================================================
  async function startRecording() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      audioContext = new AudioContext({ sampleRate: 16000 });
      var source = audioContext.createMediaStreamSource(mediaStream);
      var processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = function (e) {
        if (!recording || !ws || !wsConnected) return;
        // With barge-in on (default) the mic stays live while the model
        // talks, so the Live API's voice activity detection can interrupt
        // it; browser echo cancellation keeps the model from hearing itself.
        // data-barge-in="false" mutes the mic during playback instead
        // (useful with loud speakers in noisy rooms).
        if (!BARGE_IN && (isPlaying || micCooldown)) return;
        var input = e.inputBuffer.getChannelData(0);
        var pcm16 = new Int16Array(input.length);
        for (var i = 0; i < input.length; i++) {
          var s = Math.max(-1, Math.min(1, input[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        safeSend(
          JSON.stringify({
            type: "audio",
            data: arrayBufferToBase64(pcm16.buffer),
            mime_type: "audio/pcm;rate=16000",
          }),
        );
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      recording = true;
      addMessage("action", "Microphone on — speak to the assistant");
      sendFrame();
      startFrameLoop();
    } catch (err) {
      console.error("Microphone error:", err);
      addMessage("error", "Microphone access denied");
      switchToTextMode();
    }
  }

  function stopRecording() {
    recording = false;
    stopFrameLoop();
    if (audioContext) {
      audioContext.close().catch(function () {});
      audioContext = null;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(function (t) {
        t.stop();
      });
      mediaStream = null;
    }
  }

  function arrayBufferToBase64(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = "";
    for (var i = 0; i < bytes.byteLength; i++)
      binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  function switchToVoiceMode() {
    setTransportUi("voice");
    ensurePlaybackReady();
    if (!playbackCtx) getPlaybackContext();
    connectWebSocket(function () {
      startRecording();
    });
  }

  function switchToTextMode() {
    setTransportUi("text");
    stopRecording();
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.close();
      } catch {
        /* ignore */
      }
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    setConnectionStatus("ready");
  }

  micBtn.addEventListener("click", function () {
    if (transport === "voice") {
      switchToTextMode();
      addMessage("action", "Microphone off — text mode");
    } else {
      switchToVoiceMode();
    }
  });

  // ==================================================
  // Tool call execution (on the HOST page)
  // ==================================================
  function handleToolCalls(calls) {
    var clickedSelectors = {};
    for (var i = 0; i < calls.length; i++) {
      var call = calls[i];
      var args = call.args || {};
      var desc = args.description || args.selector || call.name;
      addMessage("action", call.name + ": " + desc);

      var result;
      if (call.name === "click_element" && clickedSelectors[args.selector]) {
        addMessage(
          "action",
          "(skipped duplicate click on " + args.selector + ")",
        );
        result = { success: true, note: "Duplicate click skipped." };
      } else {
        switch (call.name) {
          case "click_element":
            result = executeClick(args.selector, args.desired_state);
            clickedSelectors[args.selector] = true;
            break;
          case "highlight_element":
            result = executeHighlight(args.selector);
            break;
          case "type_text":
            result = executeType(args.selector, args.text);
            break;
          case "select_option":
            result = executeSelectOption(args.selector, args.value);
            break;
          case "scroll_to_element":
            result = executeScroll(args.direction);
            break;
          default:
            result = { success: false, error: "Unknown action: " + call.name };
        }
      }
      if (result && result.success === false)
        addMessage("action", "⚠ " + (result.error || "Action failed"));
      // Report the real outcome so the agent (voice or text) observes what
      // actually happened, plus the page state after the action.
      if (call.id) reportToolResult(call, result);
    }
    if (transport === "voice") schedulePageStateUpdate();
  }

  function reportToolResult(call, result) {
    // Let the page react (tab switches, dependent dropdowns) before scanning.
    setTimeout(function () {
      var payload = {
        id: call.id,
        name: call.name,
        result: result || { success: true },
        elements: scanPageElements(),
      };
      if (transport === "voice") {
        payload.type = "tool_result";
        safeSend(JSON.stringify(payload));
      } else if (sessionId) {
        payload.session_id = sessionId;
        payload.origin = window.location.hostname;
        fetch(TOOL_RESULT_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(function () {});
      }
    }, TOOL_RESULT_DELAY_MS);
  }

  // After actions change the page, send the voice agent a fresh snapshot.
  // (The page state itself comes back in each tool result.)
  var pageStateTimer = null;
  function schedulePageStateUpdate() {
    if (pageStateTimer) clearTimeout(pageStateTimer);
    pageStateTimer = setTimeout(function () {
      pageStateTimer = null;
      if (wsConnected) sendFrame();
    }, PAGE_STATE_DELAY_MS);
  }

  function ensureVisible(el) {
    var pane = el.closest(".tab-pane, [role='tabpanel']");
    if (
      pane &&
      !pane.classList.contains("active") &&
      pane.getAttribute("hidden") !== null
    ) {
      var tabId = pane.id;
      if (tabId) {
        var tab = document.querySelector(
          '[data-tab="' +
            tabId.replace("tab-", "") +
            '"], [aria-controls="' +
            tabId +
            '"]',
        );
        if (tab) tab.click();
      }
    }
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function clearHighlights() {
    document.querySelectorAll(".wf-highlight-overlay").forEach(function (h) {
      h.remove();
    });
  }

  function autoHighlight(el) {
    clearHighlights();
    setTimeout(function () {
      var rect = el.getBoundingClientRect();
      var overlay = document.createElement("div");
      overlay.className = "wf-highlight-overlay";
      overlay.style.cssText =
        "position:fixed;border:3px solid #4285f4;border-radius:8px;" +
        "box-shadow:0 0 0 4px rgba(66,133,244,0.3),0 0 20px rgba(66,133,244,0.2);" +
        "pointer-events:none;z-index:2147483646;" +
        "animation:wf-pulse 1.5s ease-in-out infinite;" +
        "top:" +
        (rect.top - 4) +
        "px;left:" +
        (rect.left - 4) +
        "px;" +
        "width:" +
        (rect.width + 8) +
        "px;height:" +
        (rect.height + 8) +
        "px;";
      document.body.appendChild(overlay);
    }, 150);
  }

  var highlightStyle = document.createElement("style");
  highlightStyle.textContent =
    "@keyframes wf-pulse{0%,100%{box-shadow:0 0 0 4px rgba(66,133,244,0.3),0 0 20px rgba(66,133,244,0.2)}50%{box-shadow:0 0 0 8px rgba(66,133,244,0.15),0 0 30px rgba(66,133,244,0.3)}}";
  document.head.appendChild(highlightStyle);

  function findTarget(selector) {
    if (!selector) return { error: "No selector given." };
    try {
      var el = document.querySelector(selector);
      return el
        ? { el: el }
        : {
            error:
              "Element not found: " +
              selector +
              ". Use a selector from the element list.",
          };
    } catch {
      return { error: "Invalid selector: " + selector };
    }
  }

  // Each executor returns {success, ...} so the agent can observe outcomes.
  function executeClick(selector, desiredState) {
    var t = findTarget(selector);
    if (t.error) return { success: false, error: t.error };
    try {
      var el = t.el;
      ensureVisible(el);
      autoHighlight(el);
      var checkbox = el.matches('input[type="checkbox"]')
        ? el
        : el.querySelector('input[type="checkbox"]');
      if (checkbox && desiredState) {
        var wantOn = desiredState.toUpperCase() === "ON";
        if (checkbox.checked === wantOn) {
          return {
            success: true,
            state: wantOn ? "ON" : "OFF",
            note: "Already in the requested state.",
          };
        }
      }
      el.click();
      if (checkbox)
        return { success: true, state: checkbox.checked ? "ON" : "OFF" };
      return { success: true };
    } catch (e) {
      console.error("executeClick:", e);
      return { success: false, error: "Click failed." };
    }
  }

  function executeHighlight(selector) {
    var t = findTarget(selector);
    if (t.error) return { success: false, error: t.error };
    try {
      ensureVisible(t.el);
      clearHighlights();
      autoHighlight(t.el);
      return { success: true };
    } catch (e) {
      console.error("executeHighlight:", e);
      return { success: false, error: "Highlight failed." };
    }
  }

  function executeType(selector, text) {
    var t = findTarget(selector);
    if (t.error) return { success: false, error: t.error };
    try {
      var el = t.el;
      ensureVisible(el);
      autoHighlight(el);
      el.focus();
      el.value = text;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return { success: true, value: el.value };
    } catch (e) {
      console.error("executeType:", e);
      return { success: false, error: "Typing failed." };
    }
  }

  function executeSelectOption(selector, value) {
    var t = findTarget(selector);
    if (t.error) return { success: false, error: t.error };
    var el = t.el;
    if (el.tagName !== "SELECT")
      return { success: false, error: selector + " is not a dropdown." };
    try {
      ensureVisible(el);
      autoHighlight(el);
      el.value = value;
      if (el.value !== value) {
        var opts = Array.from(el.options)
          .map(function (o) {
            return o.value;
          })
          .slice(0, 30);
        return {
          success: false,
          error: "Option '" + value + "' not available.",
          options: opts,
        };
      }
      el.dispatchEvent(new Event("change", { bubbles: true }));
      var opt = el.options[el.selectedIndex];
      return {
        success: true,
        selected_value: el.value,
        selected_text: opt ? opt.text : "",
      };
    } catch (e) {
      console.error("executeSelectOption:", e);
      return { success: false, error: "Select failed." };
    }
  }

  function executeScroll(direction) {
    try {
      window.scrollBy({
        top: direction === "down" ? 300 : -300,
        behavior: "smooth",
      });
      return { success: true };
    } catch (e) {
      console.error("executeScroll:", e);
      return { success: false, error: "Scroll failed." };
    }
  }

  document.addEventListener("click", function (e) {
    if (
      !e.target.closest("#wayfinder-root") &&
      !e.target.closest(".wf-highlight-overlay")
    ) {
      clearHighlights();
    }
  });

  // ==================================================
  // Screen capture (voice mode only)
  // ==================================================
  function sendFrame() {
    if (!ws || !wsConnected || sendingFrame) return;
    if (typeof html2canvas === "undefined") return;

    sendingFrame = true;
    html2canvas(document.body, {
      scale: 0.5,
      logging: false,
      useCORS: true,
      ignoreElements: function (el) {
        return el.id === "wayfinder-root";
      },
    })
      .then(function (canvas) {
        canvas.toBlob(
          function (blob) {
            sendingFrame = false;
            if (!blob) return;
            var reader = new FileReader();
            reader.onload = function () {
              safeSend(
                JSON.stringify({
                  type: "image",
                  data: reader.result.split(",")[1],
                }),
              );
            };
            reader.readAsDataURL(blob);
          },
          "image/jpeg",
          0.7,
        );
      })
      .catch(function () {
        sendingFrame = false;
      });
  }

  // Periodic low-res frames give the Live model an up-to-date view of the
  // page while the mic is on (sendFrame skips if a capture is in flight).
  function startFrameLoop() {
    stopFrameLoop();
    frameTimer = setInterval(sendFrame, FRAME_INTERVAL_MS);
  }

  function stopFrameLoop() {
    if (frameTimer) {
      clearInterval(frameTimer);
      frameTimer = null;
    }
  }

  // ==================================================
  // Page introspection
  // ==================================================
  var INTERACTIVE_SELECTOR = [
    "a[href]",
    "button",
    "input",
    "select",
    "textarea",
    "[role='button']",
    "[role='tab']",
    "[role='checkbox']",
    "[role='switch']",
    "[role='menuitem']",
    "[role='option']",
    "[role='link']",
    "[onclick]",
    "[data-testid]",
    "[contenteditable='true']",
  ].join(", ");

  function scanPageElements() {
    var elements = [];
    var seen = new Set();

    document.querySelectorAll(INTERACTIVE_SELECTOR).forEach(function (el) {
      if (el.closest("#wayfinder-root")) return;

      var selector = buildSelector(el);
      if (!selector || seen.has(selector)) return;
      seen.add(selector);

      var tag = el.tagName.toLowerCase();
      var entry = {
        selector: selector,
        tag: tag,
        type: el.type || el.getAttribute("role") || null,
        label: findLabel(el),
      };

      if (tag === "select") {
        entry.options = Array.from(el.options).map(function (o) {
          return {
            value: o.value,
            text: o.textContent.trim(),
            selected: o.selected,
          };
        });
      }

      if (el.type === "checkbox" || el.type === "radio") {
        entry.checked = el.checked;
      }

      if (
        (tag === "input" || tag === "textarea") &&
        el.type !== "checkbox" &&
        el.type !== "radio"
      ) {
        entry.value = el.value;
        entry.inputType = el.type || "text";
      }

      if (tag === "button" || tag === "a" || el.getAttribute("role")) {
        var text = el.textContent.trim();
        if (text.length > 0 && text.length < 80) entry.text = text;
      }

      var pane = el.closest(".tab-pane, [role='tabpanel']");
      if (pane && pane.id) {
        entry.tab = pane.id.replace("tab-", "");
      }

      entry.context = findContext(el);
      elements.push(entry);
    });

    return elements;
  }

  function buildSelector(el) {
    if (el.id) return "#" + CSS.escape(el.id);
    var testId = el.getAttribute("data-testid");
    if (testId) return "[data-testid='" + testId + "']";
    var ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return "[aria-label='" + CSS.escape(ariaLabel) + "']";
    if (el.name && el.closest("form")) {
      var byName = document.querySelectorAll(
        "[name='" + CSS.escape(el.name) + "']",
      );
      if (byName.length === 1) return "[name='" + CSS.escape(el.name) + "']";
    }
    return cssPath(el);
  }

  function cssPath(el) {
    var parts = [];
    var current = el;
    while (current && current !== document.body) {
      var seg = current.tagName.toLowerCase();
      if (current.id) {
        parts.unshift("#" + CSS.escape(current.id));
        break;
      }
      var parent = current.parentElement;
      if (parent) {
        var siblings = Array.from(parent.children).filter(function (c) {
          return c.tagName === current.tagName;
        });
        if (siblings.length > 1)
          seg += ":nth-of-type(" + (siblings.indexOf(current) + 1) + ")";
      }
      parts.unshift(seg);
      current = parent;
    }
    return parts.join(" > ");
  }

  function findLabel(el) {
    if (el.id) {
      var label = document.querySelector(
        "label[for='" + CSS.escape(el.id) + "']",
      );
      if (label) return label.textContent.trim();
    }
    var ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return ariaLabel;
    var labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      var refEl = document.getElementById(labelledBy);
      if (refEl) return refEl.textContent.trim();
    }
    var parentLabel = el.closest("label");
    if (parentLabel) {
      var text = parentLabel.textContent.trim();
      if (text) return text;
    }
    var group = el.closest(
      ".form-group, .setting-row, .checkbox-row, .field, .form-field, [role='group'], fieldset",
    );
    if (group) {
      var lbl = group.querySelector(
        "label, .label, .setting-label, legend, .field-label",
      );
      if (lbl && lbl !== el) return lbl.textContent.trim();
    }
    if (el.title) return el.title;
    if (el.placeholder) return el.placeholder;
    return null;
  }

  function findContext(el) {
    var ctx = {};
    var section = el.closest(
      "section, [role='tabpanel'], .tab-pane, fieldset, .settings-section, .card",
    );
    if (section) {
      var heading = section.querySelector(
        "h1, h2, h3, h4, h5, legend, .section-title",
      );
      if (heading) ctx.section = heading.textContent.trim();
    }
    var nav = el.closest("nav, [role='navigation'], [role='tablist']");
    if (nav) ctx.area = "navigation";
    return Object.keys(ctx).length > 0 ? ctx : null;
  }

  // ==================================================
  // Chat UI helpers
  // ==================================================
  function addMessage(type, text) {
    var div = document.createElement("div");
    div.className = "wf-msg " + type;
    div.textContent = text;
    chatMessages.appendChild(div);
    scrollChat();
  }

  function scrollChat() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function sendUserMessage() {
    var text = chatInput.value.trim();
    if (!text) return;

    if (transport === "voice") {
      if (!wsConnected) return;
      addMessage("user", text);
      safeSend(JSON.stringify({ type: "text", text: text }));
      chatInput.value = "";
      return;
    }

    chatInput.value = "";
    sendTextTurn(text);
  }

  chatSend.addEventListener("click", sendUserMessage);
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendUserMessage();
    }
  });

  // ==================================================
  // HTML templates
  // ==================================================
  function FAB_HTML() {
    return (
      '<button class="wf-fab" title="Open Wayfinder">' +
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>' +
      "</svg>" +
      '<span class="wf-fab-label">Ask Wayfinder</span>' +
      "</button>"
    );
  }

  function PANEL_HTML() {
    return (
      '<div class="wf-panel">' +
      '<div class="wf-header">' +
      '<div class="wf-header-left">' +
      '<div class="wf-logo">WF</div>' +
      "<div>" +
      '<div class="wf-title">Wayfinder</div>' +
      '<div class="wf-status"><span class="wf-dot ready"></span><span class="wf-status-text">Ready</span></div>' +
      "</div>" +
      "</div>" +
      '<div class="wf-header-right">' +
      '<span class="wf-mode-label text">Text</span>' +
      '<button class="wf-close-btn">&times;</button>' +
      "</div>" +
      "</div>" +
      '<div class="wf-messages">' +
      '<div class="wf-msg assistant">Hi! I\'m Wayfinder. I can answer questions from your docs and walk you through the UI. Type below, or tap the mic to switch to voice.</div>' +
      "</div>" +
      '<div class="wf-input-area">' +
      '<button class="wf-mic-btn" title="Toggle voice mode">&#127908;</button>' +
      '<input type="text" class="wf-input" placeholder="Ask anything...">' +
      '<button class="wf-send-btn">&#9654;</button>' +
      "</div>" +
      "</div>"
    );
  }

  // ==================================================
  // Widget CSS (inside shadow DOM)
  // ==================================================
  function WIDGET_CSS() {
    return (
      "" +
      '.wf-container { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; font-size: 14px; line-height: 1.5; }' +
      ".wf-fab { position: fixed; bottom: 24px; right: 24px; z-index: 2147483647; display: flex; align-items: center; gap: 8px; padding: 12px 20px; background: #1a73e8; color: white; border: none; border-radius: 28px; font-size: 15px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 16px rgba(26,115,232,0.4); transition: all 0.3s ease; }" +
      ".wf-fab:hover { background: #1557b0; transform: translateY(-2px); box-shadow: 0 6px 24px rgba(26,115,232,0.5); }" +
      ".wf-fab.hidden { transform: scale(0); opacity: 0; pointer-events: none; }" +
      ".wf-fab svg { flex-shrink: 0; }" +
      ".wf-panel { position: fixed; bottom: 24px; right: 24px; z-index: 2147483647; width: 380px; height: 560px; background: #0d0d1a; border: 1px solid #2a2a4a; border-radius: 16px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.5); transform: scale(0.8) translateY(20px); opacity: 0; pointer-events: none; transition: all 0.3s ease; transform-origin: bottom right; }" +
      ".wf-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: auto; }" +
      ".wf-header { padding: 14px 16px; border-bottom: 1px solid #2a2a4a; display: flex; align-items: center; justify-content: space-between; background: #111128; }" +
      ".wf-header-left { display: flex; align-items: center; gap: 10px; }" +
      ".wf-header-right { display: flex; align-items: center; gap: 8px; }" +
      ".wf-logo { width: 32px; height: 32px; background: linear-gradient(135deg, #1a73e8, #4ecdc4); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px; color: white; }" +
      ".wf-title { font-size: 15px; font-weight: 600; color: #e8e8f0; }" +
      ".wf-status { font-size: 11px; color: #8888a8; }" +
      ".wf-close-btn { background: none; border: none; color: #8888a8; font-size: 22px; cursor: pointer; padding: 0 4px; line-height: 1; }" +
      ".wf-close-btn:hover { color: #e8e8f0; }" +
      ".wf-mode-label { font-size: 10px; font-weight: 600; text-transform: uppercase; padding: 2px 8px; border-radius: 10px; letter-spacing: 0.5px; }" +
      ".wf-mode-label.text { background: rgba(26,115,232,0.15); color: #4a9eff; }" +
      ".wf-mode-label.voice { background: rgba(231,76,60,0.15); color: #ff6666; }" +
      ".wf-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }" +
      ".wf-dot.ready { background: #4a9eff; }" +
      ".wf-dot.connected { background: #2ecc71; }" +
      ".wf-dot.connecting { background: #f1c40f; animation: wf-blink 1s infinite; }" +
      ".wf-dot.disconnected { background: #e74c3c; }" +
      "@keyframes wf-blink { 0%,100%{opacity:1} 50%{opacity:0.3} }" +
      ".wf-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }" +
      ".wf-msg { max-width: 90%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.5; word-wrap: break-word; color: #e8e8f0; }" +
      ".wf-msg.user { align-self: flex-end; background: #1a2a3a; border: 1px solid #2a3a4a; border-bottom-right-radius: 4px; }" +
      ".wf-msg.assistant { align-self: flex-start; background: #161631; border: 1px solid #2a2a4a; border-bottom-left-radius: 4px; }" +
      ".wf-msg.action { align-self: center; background: transparent; border: 1px dashed #2a2a4a; color: #8888a8; font-size: 12px; padding: 6px 12px; max-width: 95%; }" +
      ".wf-msg.error { align-self: center; background: #2a1010; border: 1px solid #5a2020; color: #ff6666; font-size: 13px; padding: 8px 14px; }" +
      ".wf-shield { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; background: #c0392b; color: white; border-radius: 50%; font-size: 12px; flex-shrink: 0; }" +
      ".wf-input-area { padding: 12px 16px; border-top: 1px solid #2a2a4a; display: flex; gap: 8px; background: #0d0d1a; }" +
      ".wf-input { flex: 1; padding: 10px 14px; background: #1a1a36; border: 1px solid #2a2a4a; border-radius: 20px; color: #e8e8f0; font-size: 14px; outline: none; }" +
      ".wf-input:focus { border-color: #1a73e8; }" +
      ".wf-input::placeholder { color: #8888a8; }" +
      ".wf-send-btn { width: 40px; height: 40px; background: #1a73e8; border: none; border-radius: 50%; color: white; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }" +
      ".wf-send-btn:hover { background: #1557b0; }" +
      ".wf-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }" +
      ".wf-mic-btn { width: 40px; height: 40px; background: #161631; border: 1px solid #2a2a4a; border-radius: 50%; color: #8888a8; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }" +
      ".wf-mic-btn:hover { background: #1c1c3a; color: #e8e8f0; }" +
      ".wf-mic-btn.active { background: #e74c3c; border-color: #e74c3c; color: white; animation: wf-mic-pulse 1s ease-in-out infinite; }" +
      "@keyframes wf-mic-pulse { 0%,100%{box-shadow:0 0 0 0 rgba(231,76,60,0.4)} 50%{box-shadow:0 0 0 8px rgba(231,76,60,0)} }" +
      ".wf-messages::-webkit-scrollbar { width: 6px; }" +
      ".wf-messages::-webkit-scrollbar-track { background: transparent; }" +
      ".wf-messages::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 3px; }" +
      ""
    );
  }
})();
