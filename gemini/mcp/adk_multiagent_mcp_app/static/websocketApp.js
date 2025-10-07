/**
 * Copyright 2025 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 **/

/* global marked */ // Inform linting tools that 'marked' is a global variable

/**
 * @module websocketApp
 * Handles the core WebSocket chat application logic, including connection,
 * message sending/receiving, UI updates, and reconnection attempts.
 */

// --- Configuration ---
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY_MS = 5000; // 5 seconds
const ROBOT_ICON_PATH = "robot1.png"; // Ensure this path is correct relative to HTML
const THINKING_INDICATOR_ID = "thinking-indicator-wrapper";

// --- Module State ---
let ws = null; // WebSocket instance
let reconnectAttempts = 0;
let messageForm, messageInput, messagesDiv, sendButton; // DOM elements
let appInitialized = false; // Flag to prevent multiple initializations

// --- Helper Functions ---

/** Adds a system status message (e.g., connection status) to the chat UI. */
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
    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll down
  } catch (e) {
    console.error("Error adding status message:", e);
  }
}

/** Displays the 'Thinking...' indicator in the chat UI. */
function showThinkingIndicator() {
  hideThinkingIndicator(); // Clear any previous indicator
  if (!messagesDiv) {
    console.error("Cannot show thinking indicator: messagesDiv not found.");
    return;
  }
  const wrapper = document.createElement("div");
  wrapper.id = THINKING_INDICATOR_ID;
  wrapper.classList.add("message-wrapper", "thinking");

  const iconSpan = document.createElement("span");
  iconSpan.classList.add("message-icon", "robot-icon");
  const robotImg = document.createElement("img");
  robotImg.src = ROBOT_ICON_PATH;
  robotImg.alt = "Agent icon";
  iconSpan.appendChild(robotImg);

  const bubbleP = document.createElement("p");
  bubbleP.classList.add("message-bubble", "thinking-bubble");
  bubbleP.innerHTML =
    'Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span>'; // Animated dots

  wrapper.appendChild(iconSpan);
  wrapper.appendChild(bubbleP);
  messagesDiv.appendChild(wrapper);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  console.log("Showing thinking indicator.");
}

/** Removes the 'Thinking...' indicator from the chat UI. */
function hideThinkingIndicator() {
  const indicatorWrapper = document.getElementById(THINKING_INDICATOR_ID);
  if (indicatorWrapper) {
    indicatorWrapper.remove();
    console.log("Hiding thinking indicator.");
  }
}

/** Adds a user or server message to the chat UI. */
function addMessageToUI(messageText, senderType) {
  if (!messagesDiv) {
    console.error("Cannot add message: messagesDiv not found.");
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.classList.add("message-wrapper", senderType); // 'user' or 'server'

  const iconSpan = document.createElement("span");
  iconSpan.classList.add("message-icon");

  const bubbleP = document.createElement("p");
  bubbleP.classList.add("message-bubble");

  if (senderType === "user") {
    iconSpan.classList.add("user-icon");
    iconSpan.textContent = "👤";
    bubbleP.classList.add("user-message");
    bubbleP.textContent = messageText; // Display user messages as plain text
  } else {
    // Server message
    iconSpan.classList.add("robot-icon");
    const robotImg = document.createElement("img");
    robotImg.src = ROBOT_ICON_PATH;
    robotImg.alt = "Agent icon";
    iconSpan.appendChild(robotImg);
    bubbleP.classList.add("server-message-block");

    // Attempt to render server messages as Markdown
    try {
      if (typeof marked !== "undefined") {
        bubbleP.innerHTML = marked.parse(messageText); // Use marked library
      } else {
        console.warn(
          "Marked library not loaded, displaying raw server message.",
        );
        bubbleP.textContent = messageText; // Fallback
      }
    } catch (e) {
      console.error("Error parsing server Markdown:", e);
      bubbleP.textContent = messageText; // Fallback on error
      addStatusMessage(`Markdown parsing error: ${e.message}`, "error-text");
    }
  }

  wrapper.appendChild(iconSpan);
  wrapper.appendChild(bubbleP);
  messagesDiv.appendChild(wrapper);
  messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll down
}

// --- WebSocket Event Handlers ---

function handleWebSocketOpen(event) {
  console.log("WebSocket connection opened successfully:", event.target.url);
  reconnectAttempts = 0; // Reset counter
  if (sendButton) sendButton.disabled = false;
  addStatusMessage("Connection established", "connection-open-text");
  addSubmitHandler(); // Ensure form submit handler is active
}

function handleWebSocketMessage(event) {
  hideThinkingIndicator();
  try {
    const packet = JSON.parse(event.data);
    if (packet.turn_complete === true) {
      console.log("Turn complete signal received.");
      // Optionally re-enable input or other actions here
      return;
    }
    if (packet.message) {
      addMessageToUI(packet.message, "server");
    } else {
      console.warn("Received packet without 'message' field:", packet);
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
    addMessageToUI(`Received non-JSON data: ${event.data}`, "server"); // Display raw data
  }
}

function handleWebSocketClose(event) {
  console.warn(
    `WebSocket connection closed. Code: ${event.code}, Reason: '${
      event.reason || "No reason given"
    }', Was Clean: ${event.wasClean}`,
  );
  hideThinkingIndicator();
  if (sendButton) sendButton.disabled = true;
  removeSubmitHandler(); // Prevent sending on closed connection

  // Reconnection logic for unclean closures
  if (!event.wasClean && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    reconnectAttempts++;
    const reconnectDelay = Math.min(
      30000, // Max 30s delay
      RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttempts - 1), // Exponential backoff
    );
    addStatusMessage(
      `Connection closed. Attempting reconnect ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${Math.round(
        reconnectDelay / 1000,
      )}s...`,
      "connection-closed-text",
    );
    setTimeout(connectWebSocket, reconnectDelay);
  } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error("Max reconnection attempts reached.");
    addStatusMessage(
      "Connection lost permanently. Max reconnection attempts reached. Please reload the page.",
      "error-text",
    );
  } else {
    // Clean closure
    addStatusMessage("Connection closed.", "connection-closed-text");
  }
}

function handleWebSocketError(error) {
  console.error("WebSocket error occurred:", error);
  hideThinkingIndicator();
  addStatusMessage(
    "WebSocket connection error. See browser console.",
    "error-text",
  );
  // onclose will likely be called after this
}

/** Attaches all necessary event listeners to the WebSocket instance. */
function addWebSocketHandlers(webSocketInstance) {
  webSocketInstance.onopen = handleWebSocketOpen;
  webSocketInstance.onmessage = handleWebSocketMessage;
  webSocketInstance.onclose = handleWebSocketClose;
  webSocketInstance.onerror = handleWebSocketError;
  console.log("WebSocket event handlers attached for:", webSocketInstance.url);
}

// --- Form Submission ---

/** Handles the message form submission. */
function submitMessageHandler(e) {
  e.preventDefault(); // Prevent page reload

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn("Attempted send, but WebSocket is not open.");
    addStatusMessage(
      "Cannot send message - Connection not active.",
      "error-text",
    );
    return false;
  }
  if (!messageInput) {
    console.error("Cannot send message: messageInput is missing.");
    return false;
  }

  const messageText = messageInput.value.trim();
  if (messageText) {
    addMessageToUI(messageText, "user");
    showThinkingIndicator();
    try {
      console.log("Sending message:", messageText);
      ws.send(messageText); // Send raw text
      messageInput.value = ""; // Clear input
      messageInput.focus();
    } catch (error) {
      console.error("Error sending message via WebSocket:", error);
      hideThinkingIndicator();
      addStatusMessage(
        `Failed to send message: ${error.message}`,
        "error-text",
      );
      // Add visual feedback to the failed user message
      const lastUserBubble = messagesDiv?.querySelector(
        ".message-wrapper.user:last-child .message-bubble",
      );
      if (lastUserBubble) {
        const errorSpan = document.createElement("span");
        errorSpan.textContent = " (Send Error)";
        errorSpan.style.color = "var(--status-error, #dc3545)"; // Use CSS var or fallback
        errorSpan.style.fontSize = "0.8em";
        lastUserBubble.appendChild(errorSpan);
      }
    }
  } else {
    console.log("Empty message submission ignored.");
  }
  return false; // Prevent default just in case
}

/** Attaches the submit event listener to the form. */
function addSubmitHandler() {
  if (messageForm && submitMessageHandler) {
    messageForm.removeEventListener("submit", submitMessageHandler); // Prevent duplicates
    messageForm.addEventListener("submit", submitMessageHandler);
    console.log("Submit handler assigned to form.");
  } else {
    console.error(
      "Cannot add submit handler: Message form or handler missing!",
    );
  }
}

/** Removes the submit event listener from the form. */
function removeSubmitHandler() {
  if (messageForm && submitMessageHandler) {
    messageForm.removeEventListener("submit", submitMessageHandler);
    console.log("Submit handler removed from form.");
  }
}

// --- WebSocket Connection ---

/** Establishes or re-establishes the WebSocket connection. */
function connectWebSocket() {
  // Generate session ID and URL only when connecting
  const sessionId = Math.random().toString(36).substring(2, 15);
  const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
  const wsUrl = wsProtocol + window.location.host + "/ws/" + sessionId;

  console.log(
    `Attempting WebSocket connect: ${wsUrl} (Attempt: ${reconnectAttempts + 1})`,
  );

  try {
    // Ensure any previous connection is closed before creating a new one
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      console.log("Closing existing WebSocket before reconnecting.");
      ws.close(1000, "Reconnecting"); // 1000 = Normal Closure
    }

    ws = new WebSocket(wsUrl);
    addWebSocketHandlers(ws); // Attach handlers to the new instance
  } catch (error) {
    console.error("Error creating WebSocket instance:", error);
    addStatusMessage(
      `Failed to initialize connection: ${error.message}`,
      "error-text",
    );
    // Attempt retry if creation fails (similar to onclose logic)
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      const reconnectDelay = Math.min(
        30000,
        RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttempts - 1),
      );
      addStatusMessage(
        `Retrying connection in ${Math.round(reconnectDelay / 1000)}s...`,
        "connection-closed-text",
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

// --- Initialization ---

/**
 * Initializes the WebSocket application. Finds necessary DOM elements
 * and initiates the first WebSocket connection attempt.
 */
export function initWebSocketApp() {
  if (appInitialized) {
    console.warn("WebSocket app already initialized. Skipping.");
    return;
  }

  console.log("Initializing WebSocket application logic...");

  // Find essential DOM elements
  messageForm = document.getElementById("message-form");
  messageInput = document.getElementById("message");
  messagesDiv = document.getElementById("messages");
  sendButton = document.getElementById("send-button");
  const appTab = document.getElementById("app-tab-content"); // Container for error messages

  // Critical check for UI elements
  if (!messageForm || !messageInput || !messagesDiv || !sendButton) {
    console.error("CRITICAL: One or more required app DOM elements not found!");
    const errorMsg =
      "<p class='system-status-message'><span class='error-text'>Initialization Error: Required UI elements missing. App cannot start.</span></p>";
    if (appTab) {
      const appContainer = appTab.querySelector(".app-container"); // Try to find inner container
      if (appContainer) appContainer.innerHTML = errorMsg;
      else appTab.innerHTML = errorMsg; // Fallback to replacing tab content
    } else {
      // Fallback if even the app tab is missing
      alert(
        "Initialization Error: App UI elements missing and app tab not found.",
      );
    }
    return; // Stop initialization
  }

  console.log("App UI Elements successfully located.");
  if (sendButton) sendButton.disabled = true; // Disable send until connected

  appInitialized = true; // Mark as initialized
  connectWebSocket(); // Start the connection process
  console.log("WebSocket App module initialized and connection initiated.");
}
