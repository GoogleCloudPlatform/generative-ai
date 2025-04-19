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
    if (typeof marked === "undefined") {
      console.error("Marked library not loaded. Cannot render markdown.");
      userGuideContentDiv.innerHTML =
        "<p class='error-text'>Error: Markdown library (marked.js) not available. Make sure it's linked in the HTML.</p>";
      return;
    }

    userGuideContentDiv.innerHTML = "<p><i>Loading guide content...</i></p>";

    fetch(markdownFilePath)
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `HTTP error ${response.status} - Could not fetch '${markdownFilePath}'. Make sure the file exists and the page is served via HTTP(S).`,
          );
        }
        return response.text();
      })
      .then((markdownText) => {
        try {
          // Use marked.parse() instead of just marked() for v4+
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
          throw parseError; // Rethrow to be caught by the outer catch
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
  const messageForm = document.getElementById("message-form");
  const messageInput = document.getElementById("message");
  const messagesDiv = document.getElementById("messages");
  const sendButton = document.getElementById("send-button");

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
      // Fallback if even the app tab is missing
      alert(
        "Initialization Error: App UI elements missing and app tab not found.",
      );
    }
    return; // Stop script execution if essential elements are missing
  }
  console.log("App UI Elements successfully located.");

  const sessionId = Math.random().toString(36).substring(2, 15);
  const ws_protocol =
    window.location.protocol === "https:" ? "wss://" : "ws://";
  // Construct the WebSocket URL relative to the current host
  const ws_url = ws_protocol + window.location.host + "/ws/" + sessionId;
  let ws = null;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  const reconnectBaseDelay = 5000; // 5 seconds base delay

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
      span.className = typeClass; // e.g., "connection-open-text", "error-text"
      span.textContent = text;
      p.appendChild(span);
      messagesDiv.appendChild(p);
      // Scroll to the bottom to make the new message visible
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (e) {
      console.error("Error adding status message:", e);
    }
  }

  function showThinkingIndicator() {
    hideThinkingIndicator(); // Clear any previous indicator first
    if (!messagesDiv) {
      console.error("Cannot show thinking indicator: messagesDiv not found.");
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.id = "thinking-indicator-wrapper"; // Assign an ID for easy removal
    wrapper.classList.add("message-wrapper", "thinking");

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("message-icon", "robot-icon");
    const robotImg = document.createElement("img");
    // IMPORTANT: Ensure robot1.png is accessible relative to your HTML file
    robotImg.src = "robot1.png"; // Make sure this path is correct
    robotImg.alt = "Agent icon";
    iconSpan.appendChild(robotImg);

    const bubbleP = document.createElement("p");
    bubbleP.classList.add("message-bubble", "thinking-bubble");
    bubbleP.innerHTML =
      'Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span>'; // Animated dots

    wrapper.appendChild(iconSpan);
    wrapper.appendChild(bubbleP);
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to bottom
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
    // senderType = 'user' or 'server'
    if (!messagesDiv) {
      console.error("Cannot add message: messagesDiv not found.");
      return;
    }

    const wrapper = document.createElement("div");
    wrapper.classList.add("message-wrapper", senderType); // e.g., 'message-wrapper user'

    const iconSpan = document.createElement("span");
    iconSpan.classList.add("message-icon");

    const bubbleP = document.createElement("p");
    bubbleP.classList.add("message-bubble");

    if (senderType === "user") {
      iconSpan.classList.add("user-icon");
      iconSpan.textContent = "👤"; // User icon
      bubbleP.classList.add("user-message");
      // Display user messages as plain text for security and simplicity
      bubbleP.textContent = messageText;
    } else {
      // server message
      iconSpan.classList.add("robot-icon");
      const robotImg = document.createElement("img");
      // IMPORTANT: Ensure robot1.png is accessible from the HTML's location
      robotImg.src = "robot1.png";
      robotImg.alt = "Agent icon";
      iconSpan.appendChild(robotImg);

      bubbleP.classList.add("server-message-block");
      // Attempt to render server messages as Markdown
      try {
        if (typeof marked !== "undefined") {
          // Render Markdown using marked.parse()
          bubbleP.innerHTML = marked.parse(messageText);
        } else {
          console.warn(
            "Marked library not loaded, displaying raw server message.",
          );
          bubbleP.textContent = messageText; // Fallback to plain text
        }
      } catch (e) {
        console.error("Error parsing server Markdown:", e);
        // Display raw text as a fallback if Markdown parsing fails
        bubbleP.textContent = messageText;
        addStatusMessage(`Markdown parsing error: ${e.message}`, "error-text");
      }
    }

    wrapper.appendChild(iconSpan);
    wrapper.appendChild(bubbleP);
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to keep latest message visible
  }

  function addWebSocketHandlers(webSocketInstance) {
    webSocketInstance.onopen = () => {
      console.log(
        "WebSocket connection opened successfully:",
        webSocketInstance.url,
      );
      reconnectAttempts = 0; // Reset reconnect counter on successful connection
      if (sendButton) sendButton.disabled = false;
      else console.warn("sendButton not found in onopen");
      addStatusMessage("Connection established", "connection-open-text");
      addSubmitHandler(); // Ensure form submit handler is active
    };

    webSocketInstance.onmessage = (event) => {
      hideThinkingIndicator(); // Server responded, hide "Thinking..."
      try {
        const packet = JSON.parse(event.data);
        // Check if it's just a turn completion signal (optional, based on your backend)
        if (packet.turn_complete === true) {
          console.log("Turn complete signal received.");
          // Potentially re-enable input or perform other actions here if needed
          return; // Don't display this as a message
        }
        // Add the message content to the UI
        if (packet.message) {
          addMessageToUI(packet.message, "server");
        } else {
          console.log("Received packet without 'message' field:", packet);
          // Optionally display a generic message or ignore
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
        // Display the raw data as a fallback, indicating it wasn't valid JSON
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
      // Remove the submit handler to prevent sending messages on a closed connection
      if (messageForm) messageForm.onsubmit = null;

      // Implement reconnection logic only if the closure was not clean or unexpected
      // Adjust this condition based on your expected close codes if necessary
      if (!event.wasClean && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        // Exponential backoff for reconnect delay
        const reconnectDelay = Math.min(
          30000,
          reconnectBaseDelay * Math.pow(2, reconnectAttempts - 1),
        ); // Max 30s
        addStatusMessage(
          `Connection closed. Attempting reconnect ${reconnectAttempts}/${maxReconnectAttempts} in ${Math.round(
            reconnectDelay / 1000,
          )}s...`,
          "connection-closed-text",
        );
        setTimeout(connectWebSocket, reconnectDelay);
      } else if (reconnectAttempts >= maxReconnectAttempts) {
        console.error("Max reconnection attempts reached.");
        addStatusMessage(
          "Connection lost permanently. Max reconnection attempts reached. Please reload the page.",
          "error-text",
        );
      } else {
        // Connection closed cleanly (e.g., server shutdown, explicit close)
        addStatusMessage("Connection closed.", "connection-closed-text");
      }
    };

    webSocketInstance.onerror = (error) => {
      console.error("WebSocket error occurred:", error);
      hideThinkingIndicator();
      // Provide a generic error message, details are in the console
      addStatusMessage(
        "WebSocket connection error. See browser console for details.",
        "error-text",
      );
      // Note: 'onclose' will likely be called immediately after 'onerror'
    };

    console.log(
      "WebSocket event handlers attached for:",
      webSocketInstance.url,
    );
  }

  // Named function for the submit event handler
  function submitMessageHandler(e) {
    e.preventDefault(); // Prevent default form submission (page reload)

    // Check if WebSocket is connected and ready
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn("Attempted send, but WebSocket is not open.");
      addStatusMessage(
        "Cannot send message - Connection is not active.",
        "error-text",
      );
      return false; // Indicate failure
    }
    if (!messageInput || !messagesDiv) {
      console.error(
        "Cannot submit message: messageInput or messagesDiv not found.",
      );
      return false; // Indicate failure
    }

    const messageText = messageInput.value.trim(); // Get message and remove whitespace
    if (messageText) {
      addMessageToUI(messageText, "user"); // Display user's message
      showThinkingIndicator(); // Show "Thinking..." indicator
      try {
        console.log("Sending message:", messageText);
        ws.send(messageText); // Send the message text via WebSocket
        messageInput.value = ""; // Clear the input field
        messageInput.focus(); // Keep focus on the input field
      } catch (error) {
        console.error("Error sending message via WebSocket:", error);
        hideThinkingIndicator(); // Hide indicator on send error
        addStatusMessage(
          `Failed to send message: ${error.message}`,
          "error-text",
        );
        // Optionally add visual feedback to the failed user message bubble
        const lastUserBubble = messagesDiv.querySelector(
          ".message-wrapper.user:last-child .message-bubble",
        );
        if (lastUserBubble) {
          const errorSpan = document.createElement("span");
          errorSpan.textContent = " (Send Error)";
          errorSpan.style.color = "var(--status-error)"; // Use CSS variable for error color
          errorSpan.style.fontSize = "0.8em";
          lastUserBubble.appendChild(errorSpan);
        }
      }
    } else {
      console.log("Empty message submission ignored.");
    }
    return false; // Prevent default form submission behaviour
  }

  // Function to attach the submit handler to the form
  function addSubmitHandler() {
    if (messageForm) {
      // Remove existing listener first to prevent duplicates if called multiple times
      messageForm.removeEventListener("submit", submitMessageHandler);
      // Add the listener
      messageForm.addEventListener("submit", submitMessageHandler);
      console.log("Submit handler assigned to form.");
    } else {
      console.error("Cannot add submit handler: Message form not found!");
    }
  }

  // Function to establish the WebSocket connection
  function connectWebSocket() {
    // Pre-check: Ensure required UI elements exist before attempting connection
    if (!messageForm || !messageInput || !messagesDiv || !sendButton) {
      console.error("Cannot connect WebSocket: Essential UI elements missing.");
      // Optionally display an error in the UI here as well
      return;
    }

    console.log(
      `Attempting WebSocket connect: ${ws_url} (Attempt: ${
        reconnectAttempts + 1
      })`,
    );
    //addStatusMessage(
    //  `Connecting to server (Attempt ${reconnectAttempts + 1})...`,
    //  "tertiary-text-color"
    //);

    try {
      // Close any existing non-closed connection before creating a new one
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        console.log(
          "Closing existing WebSocket connection before reconnecting.",
        );
        ws.close(1000, "Reconnecting"); // Close gracefully if possible
      }
      // Create the new WebSocket instance
      ws = new WebSocket(ws_url);
      // Attach all event handlers (onopen, onmessage, onclose, onerror)
      addWebSocketHandlers(ws);
    } catch (error) {
      console.error("Error creating WebSocket instance:", error);
      addStatusMessage(
        `Failed to initialize connection: ${error.message}`,
        "error-text",
      );
      // Attempt to reconnect if creation fails and under the limit
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const reconnectDelay = Math.min(
          30000,
          reconnectBaseDelay * Math.pow(2, reconnectAttempts - 1),
        );
        addStatusMessage(
          `Retrying connection in ${Math.round(reconnectDelay / 1000)}s...`,
          "connection-closed-text",
        );
        setTimeout(connectWebSocket, reconnectDelay);
      } else {
        addStatusMessage(
          "Failed to initialize connection after multiple attempts. Please reload the page.",
          "error-text",
        );
      }
    }
  }

  // --- Initial Connection ---
  // Start the connection process only if the essential UI elements were found initially
  if (messageForm && messageInput && messagesDiv && sendButton) {
    console.log("Starting initial WebSocket connection...");
    connectWebSocket();
  } else {
    console.error(
      "WebSocket connection not started due to missing UI elements during initialization.",
    );
    // Error message should already be displayed by the initial check
  }
}); // End DOMContentLoaded
