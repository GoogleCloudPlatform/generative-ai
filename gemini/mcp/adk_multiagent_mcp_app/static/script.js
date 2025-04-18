/**
 * Copyright 2025 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 **/

/* global marked */

document.addEventListener("DOMContentLoaded", () => {
  // <<<--- MODIFIED: Removed unused 'event' parameter
  console.log("DOM fully loaded and parsed");

  // --- Tab Switching Logic ---
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetPanelId = button.getAttribute("data-tab");
      const targetPanel = document.getElementById(targetPanelId);

      tabButtons.forEach((btn) => btn.classList.remove("active"));
      tabPanels.forEach((panel) => panel.classList.remove("active"));

      button.classList.add("active");
      if (targetPanel) {
        targetPanel.classList.add("active");
        console.log(`Switched to tab: ${targetPanelId}`);
      } else {
        console.error(`Target panel with ID ${targetPanelId} not found.`);
      }
    });
  });
  console.log("Tab switching logic initialized.");

  // --- Function to Load and Render User Guide Markdown ---
  const userGuideContentDiv = document.getElementById(
    "user-guide-markdown-content",
  );
  const markdownFilePath = "user_guide.md"; // <<<--- MAKE SURE THIS FILE EXISTS!

  function loadUserGuide() {
    if (!userGuideContentDiv) {
      console.error("User guide container div not found.");
      return;
    }
    // Check if 'marked' exists (confirming the need for the /* global */ directive)
    if (typeof marked === "undefined") {
      console.error("Marked library not loaded. Cannot render markdown.");
      userGuideContentDiv.innerHTML =
        "<p class='error-text'>Error: Markdown library (marked.js) not available.</p>";
      return;
    }

    userGuideContentDiv.innerHTML = "<p><i>Loading guide content...</i></p>";

    fetch(markdownFilePath)
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `HTTP error ${response.status} - Could not fetch '${markdownFilePath}'.`,
          );
        }
        return response.text();
      })
      .then((markdownText) => {
        try {
          // Use 'marked' which the linter now knows is global
          userGuideContentDiv.innerHTML = marked.parse(markdownText);
          console.log(
            "User guide markdown loaded and rendered from file:",
            markdownFilePath,
          );
        } catch (parseError) {
          console.error("Error parsing Markdown:", parseError);
          userGuideContentDiv.innerHTML = `<p class='error-text'>Error rendering guide content.</p><p>Raw content:</p><pre>${markdownText
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")}</pre>`;
          throw parseError;
        }
      })
      .catch((error) => {
        console.error("Error loading or rendering user guide:", error);
        userGuideContentDiv.innerHTML = `<p class='error-text'>Failed to load user guide: ${error.message}.</p>`;
      });
  }

  loadUserGuide();

  // --- Original WebSocket App Logic ---
  console.log("Initializing WebSocket application logic...");
  const messageForm = document.getElementById("message-form"); // Adjusted based on previous CSS fix
  const messageInput = document.getElementById("message");
  const messagesDiv = document.getElementById("messages");
  const sendButton = document.getElementById("send-button"); // Adjusted based on previous CSS fix

  // Check elements using potentially updated IDs
  if (!messageForm || !messageInput || !messagesDiv || !sendButton) {
    console.error("CRITICAL: One or more required app DOM elements not found!");
    const appTab = document.getElementById("app-tab-content");
    const errorMsg =
      "<p class='system-status-message'><span class='error-text'>Initialization Error: Required UI elements missing. App cannot start.</span></p>";
    if (appTab) {
      const appContainer = appTab.querySelector(".app-container");
      if (appContainer) appContainer.innerHTML = errorMsg;
      else appTab.innerHTML = errorMsg;
    } else {
      alert(
        "Initialization Error: App UI elements missing and app tab not found.",
      );
    }
    return;
  }
  console.log("App UI Elements successfully located.");

  const sessionId = Math.random().toString(36).substring(2, 15);
  const ws_protocol =
    window.location.protocol === "https:" ? "wss://" : "ws://";
  const ws_url = ws_protocol + window.location.host + "/ws/" + sessionId;
  let ws = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  const reconnectBaseDelay = 5000;

  // --- WebSocket Helper Functions ---

  function addStatusMessage(text, typeClass) {
    if (!messagesDiv) {
      console.error("Cannot add status message: messagesDiv not found.");
      return;
    }
    try {
      const p = document.createElement("p");
      p.classList.add("system-status-message");
      const span = document.createElement("span");
      span.className = typeClass;
      span.textContent = text;
      p.appendChild(span);
      messagesDiv.appendChild(p);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (e) {
      console.error("Error adding status message:", e);
    }
  }

  function showThinkingIndicator() {
    hideThinkingIndicator(); // Clear previous
    if (!messagesDiv) {
      console.error("Cannot show thinking indicator: messagesDiv not found.");
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.id = "thinking-indicator-wrapper";
    wrapper.classList.add("message-wrapper", "thinking");

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("message-icon", "robot-icon");
    const robotImg = document.createElement("img");
    // IMPORTANT: Ensure robot1.png is accessible relative to your HTML file
    robotImg.src = "robot1.png";
    robotImg.alt = "Agent icon";
    iconSpan.appendChild(robotImg);

    const bubbleP = document.createElement("p");
    bubbleP.classList.add("message-bubble", "thinking-bubble");
    bubbleP.innerHTML =
      'Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span>';

    wrapper.appendChild(iconSpan);
    wrapper.appendChild(bubbleP);
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    console.log("Showing thinking indicator.");
  }

  function hideThinkingIndicator() {
    const indicatorWrapper = document.getElementById(
      "thinking-indicator-wrapper",
    );
    if (indicatorWrapper) {
      indicatorWrapper.remove();
      console.log("Hiding thinking indicator.");
    }
  }

  function addMessageToUI(messageText, senderType) {
    // type = 'user' or 'server'
    if (!messagesDiv) {
      console.error("Cannot add message: messagesDiv not found.");
      return;
    }

    const wrapper = document.createElement("div");
    wrapper.classList.add("message-wrapper", senderType);

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("message-icon");

    const bubbleP = document.createElement("p");
    bubbleP.classList.add("message-bubble");

    if (senderType === "user") {
      iconSpan.classList.add("user-icon");
      iconSpan.textContent = "👤";
      bubbleP.classList.add("user-message");
      bubbleP.textContent = messageText; // User messages as plain text
    } else {
      // server
      iconSpan.classList.add("robot-icon");
      const robotImg = document.createElement("img");
      // IMPORTANT: Ensure robot1.png is accessible
      robotImg.src = "robot1.png";
      robotImg.alt = "Agent icon";
      iconSpan.appendChild(robotImg);

      bubbleP.classList.add("server-message-block");
      try {
        // Check if 'marked' exists and use it
        if (typeof marked !== "undefined") {
          // Render Markdown
          bubbleP.innerHTML = marked.parse(messageText);
        } else {
          console.warn(
            "Marked library not loaded, displaying raw server message.",
          );
          bubbleP.textContent = messageText;
        }
      } catch (e) {
        console.error("Error parsing server Markdown:", e);
        bubbleP.textContent = messageText; // Fallback
        addStatusMessage(`Markdown parsing error: ${e.message}`, "error-text");
      }
    }

    wrapper.appendChild(iconSpan);
    wrapper.appendChild(bubbleP);
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function addWebSocketHandlers(webSocketInstance) {
    webSocketInstance.onopen = () => {
      console.log("WebSocket connection opened successfully.");
      reconnectAttempts = 0;
      if (sendButton) sendButton.disabled = false;
      else console.warn("sendButton not found in onopen");
      addStatusMessage("Connection established", "connection-open-text");
      addSubmitHandler();
    };

    webSocketInstance.onmessage = (event) => {
      hideThinkingIndicator();
      try {
        const packet = JSON.parse(event.data);
        if (packet.turn_complete === true) {
          console.log("Turn complete signal received.");
          return;
        }
        if (packet.message) {
          addMessageToUI(packet.message, "server");
        } else {
          console.log("Received packet without 'message' field:", packet);
        }
      } catch (parseError) {
        console.error(
          "Error parsing WebSocket message:",
          parseError,
          "Raw data:",
          event.data,
        );
        addStatusMessage(
          `Error processing server message: ${parseError.message}`,
          "error-text",
        );
        addMessageToUI(`Received non-JSON data: ${event.data}`, "server");
      }
    };

    webSocketInstance.onclose = (event) => {
      console.warn(
        `WebSocket connection closed. Code: ${event.code}, Reason: '${
          event.reason || "No reason given"
        }', Was Clean: ${event.wasClean}`,
      );
      hideThinkingIndicator();
      if (sendButton) sendButton.disabled = true;
      else console.warn("sendButton not found in onclose");
      if (messageForm) messageForm.onsubmit = null;

      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const reconnectDelay = Math.min(
          30000,
          reconnectBaseDelay * Math.pow(2, reconnectAttempts - 1),
        );
        addStatusMessage(
          `Connection closed. Attempting reconnect ${reconnectAttempts}/${maxReconnectAttempts} in ${Math.round(
            reconnectDelay / 1000,
          )}s...`,
          "connection-closed-text",
        );
        setTimeout(connectWebSocket, reconnectDelay);
      } else {
        console.error("Max reconnection attempts reached.");
        addStatusMessage(
          "Connection lost permanently. Max reconnection attempts reached. Please reload the page.",
          "error-text",
        );
      }
    };

    webSocketInstance.onerror = (error) => {
      console.error("WebSocket error occurred:", error);
      hideThinkingIndicator();
      addStatusMessage(
        "WebSocket error occurred. See browser console.",
        "error-text",
      );
    };

    console.log(
      "WebSocket event handlers attached for:",
      webSocketInstance.url,
    );
  }

  function submitMessageHandler(e) {
    e.preventDefault();
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn("Attempted send, but WebSocket is not open.");
      addStatusMessage(
        "Cannot send message - Connection is not active.",
        "error-text",
      );
      return false;
    }
    if (!messageInput || !messagesDiv) {
      console.error(
        "Cannot submit message: messageInput or messagesDiv not found.",
      );
      return false;
    }

    const messageText = messageInput.value.trim();
    if (messageText) {
      addMessageToUI(messageText, "user");
      showThinkingIndicator();
      try {
        console.log("Sending message:", messageText);
        ws.send(messageText);
        messageInput.value = "";
        messageInput.focus();
      } catch (error) {
        console.error("Error sending message via WebSocket:", error);
        hideThinkingIndicator();
        addStatusMessage(
          `Failed to send message: ${error.message}`,
          "error-text",
        );
        const lastUserBubble = messagesDiv.querySelector(
          ".message-wrapper.user:last-child .message-bubble",
        );
        if (lastUserBubble) {
          const errorSpan = document.createElement("span");
          errorSpan.textContent = " (Send Error)";
          errorSpan.style.color = "var(--status-error)"; // Use variable
          errorSpan.style.fontSize = "0.8em";
          lastUserBubble.appendChild(errorSpan);
        }
      }
    } else {
      console.log("Empty message submission ignored.");
    }
    return false;
  }

  function addSubmitHandler() {
    if (messageForm) {
      messageForm.removeEventListener("submit", submitMessageHandler);
      messageForm.addEventListener("submit", submitMessageHandler);
      console.log("Submit handler assigned to form.");
    } else {
      console.error("Cannot add submit handler: Message form not found!");
    }
  }

  function connectWebSocket() {
    if (!messageForm || !messageInput || !messagesDiv || !sendButton) return;

    console.log(
      `Attempting WebSocket connect: ${ws_url} (Attempt: ${
        reconnectAttempts + 1
      })`,
    );

    try {
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        console.log(
          "Closing existing WebSocket connection before reconnecting.",
        );
        ws.close();
      }
      ws = new WebSocket(ws_url);
      addWebSocketHandlers(ws);
    } catch (error) {
      console.error("Error creating WebSocket:", error);
      addStatusMessage(
        `Failed to initialize connection: ${error.message}`,
        "error-text",
      );
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const reconnectDelay = Math.min(
          30000,
          reconnectBaseDelay * Math.pow(2, reconnectAttempts - 1),
        );
        setTimeout(connectWebSocket, reconnectDelay);
      } else {
        addStatusMessage(
          "Failed to initialize connection after multiple attempts. Please reload.",
          "error-text",
        );
      }
    }
  }

  // Start connection only if UI elements are present
  if (messageForm && messageInput && messagesDiv && sendButton) {
    console.log("Starting WebSocket connection...");
    connectWebSocket();
  } else {
    console.error(
      "WebSocket connection not started due to missing UI elements.",
    );
  }
}); // End DOMContentLoaded
