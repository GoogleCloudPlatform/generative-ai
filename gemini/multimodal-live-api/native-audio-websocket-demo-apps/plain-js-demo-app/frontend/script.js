/**
 * Main application script for Gemini Live API Demo
 * Handles UI interactions, media streaming, and communication with Gemini API
 */

// Global state
const state = {
  client: null,
  audio: { streamer: null, player: null, isStreaming: false },
  video: { streamer: null, isStreaming: false },
  screen: { capture: null, isSharing: false },
};

// DOM element cache
const elements = {};

// Initialize DOM references
function initDOM() {
  const ids = [
    "projectId",
    "model",
    "proxyUrl",
    "systemInstructions",
    "enableInputTranscription",
    "enableOutputTranscription",
    "enableGrounding",
    "enableAffectiveDialog",
    "enableAlertTool",
    "enableCssStyleTool",
    "enableProactiveAudio",
    "voiceSelect",
    "temperature",
    "temperatureValue",
    "disableActivityDetection",
    "silenceDuration",
    "prefixPadding",
    "endSpeechSensitivity",
    "startSpeechSensitivity",
    "activityHandling",
    "connectBtn",
    "disconnectBtn",
    "connectionStatus",
    "startAudioBtn",
    "startVideoBtn",
    "startScreenBtn",
    "videoPreview",
    "micSelect",
    "cameraSelect",
    "volume",
    "volumeValue",
    "chatContainer",
    "chatInput",
    "sendBtn",
    "debugInfo",
    "setupJsonSection",
    "setupJsonDisplay",
  ];

  ids.forEach((id) => {
    elements[id] = document.getElementById(id);
  });
}

// Populate media device selectors
async function populateMediaDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();

    // Clear existing options
    elements.micSelect.innerHTML =
      '<option value="">Default Microphone</option>';
    elements.cameraSelect.innerHTML =
      '<option value="">Default Camera</option>';

    // Add audio input devices
    devices
      .filter((device) => device.kind === "audioinput")
      .forEach((device) => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent =
          device.label || `Microphone ${device.deviceId.substr(0, 8)}`;
        elements.micSelect.appendChild(option);
      });

    // Add video input devices
    devices
      .filter((device) => device.kind === "videoinput")
      .forEach((device) => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent =
          device.label || `Camera ${device.deviceId.substr(0, 8)}`;
        elements.cameraSelect.appendChild(option);
      });
  } catch (error) {
    console.error("Error enumerating devices:", error);
  }
}

// Create reusable message element
function createMessage(text, className = "") {
  const div = document.createElement("div");
  div.textContent = text;
  if (className) div.className = className;
  return div;
}

// Update status display
function updateStatus(elementId, text) {
  if (elements[elementId]) {
    elements[elementId].textContent = text;
  }
}

// Connect to Gemini
async function connect() {
  const proxyUrl = elements.proxyUrl.value || null;
  const projectId = elements.projectId.value;
  const model = elements.model.value;

  if (!proxyUrl && !projectId) {
    alert("Please provide either a Proxy URL and Project ID");
    return;
  }

  try {
    updateStatus("connectionStatus", "Connecting...");

    // Create GeminiLiveAPI instance directly
    state.client = new GeminiLiveAPI(proxyUrl, projectId, model);

    // Configure settings
    state.client.systemInstructions = elements.systemInstructions.value;
    state.client.inputAudioTranscription =
      elements.enableInputTranscription.checked;
    state.client.outputAudioTranscription =
      elements.enableOutputTranscription.checked;
    state.client.googleGrounding = elements.enableGrounding.checked;
    state.client.enableAffectiveDialog = elements.enableAffectiveDialog.checked;
    state.client.responseModalities = ["AUDIO"];
    state.client.voiceName = elements.voiceSelect.value;
    state.client.temperature = parseFloat(elements.temperature.value);

    // Set proactivity configuration
    state.client.proactivity = {
      proactiveAudio: elements.enableProactiveAudio.checked,
    };

    // Set automatic activity detection configuration
    state.client.automaticActivityDetection = {
      disabled: elements.disableActivityDetection.checked,
      silence_duration_ms: parseInt(elements.silenceDuration.value),
      prefix_padding_ms: parseInt(elements.prefixPadding.value),
      end_of_speech_sensitivity: elements.endSpeechSensitivity.value,
      start_of_speech_sensitivity: elements.startSpeechSensitivity.value,
    };

    // Set activity handling
    state.client.activityHandling = elements.activityHandling.value;

    // Add custom tools only if Google grounding is disabled
    const isGroundingEnabled = elements.enableGrounding.checked;

    if (!isGroundingEnabled) {
      // Add alert tool if enabled
      if (elements.enableAlertTool.checked) {
        const alertTool = new ShowAlertTool();
        state.client.addFunction(alertTool);
        console.log("✅ Alert tool enabled");
      }

      // Add CSS style tool if enabled
      if (elements.enableCssStyleTool.checked) {
        const cssStyleTool = new AddCSSStyleTool();
        state.client.addFunction(cssStyleTool);
        console.log("✅ CSS style tool enabled");
      }
    } else {
      console.log(
        "⚠️ Custom tools disabled due to Google grounding being enabled"
      );
    }

    // Set callbacks
    state.client.onReceiveResponse = handleMessage;
    state.client.onError = handleError;
    state.client.onOpen = handleOpen;
    state.client.onClose = handleClose;

    await state.client.connect();

    // Initialize media handlers
    state.audio.streamer = new AudioStreamer(state.client);
    state.video.streamer = new VideoStreamer(state.client);
    state.screen.capture = new ScreenCapture(state.client);
    state.audio.player = new AudioPlayer();
    await state.audio.player.init();

    updateStatus("debugInfo", "Connected successfully");
  } catch (error) {
    console.error("Connection failed:", error);
    updateStatus("connectionStatus", "Connection failed: " + error.message);
    updateStatus("debugInfo", "Error: " + error.message);
  }
}

// Disconnect
function disconnect() {
  if (state.client && state.client.webSocket) {
    state.client.webSocket.close();
    state.client = null;
  }

  // Stop all streams
  if (state.audio.streamer) state.audio.streamer.stop();
  if (state.video.streamer) state.video.streamer.stop();
  if (state.screen.capture) state.screen.capture.stop();

  // Reset states
  state.audio.isStreaming = false;
  state.video.isStreaming = false;
  state.screen.isSharing = false;

  // Update UI
  updateStatus("connectionStatus", "Disconnected");

  elements.startAudioBtn.textContent = "Start Audio";
  elements.startVideoBtn.textContent = "Start Video";
  elements.startScreenBtn.textContent = "Share Screen";

  elements.videoPreview.hidden = true;
  elements.videoPreview.srcObject = null;
}

// Handle messages
function handleMessage(message) {
  console.log("Message:", message);
  updateStatus("debugInfo", `Message: ${message.type}`);

  switch (message.type) {
    case MultimodalLiveResponseType.TEXT:
      console.log("Text message:");
      addMessage(message.data, "assistant");
      break;

    case MultimodalLiveResponseType.AUDIO:
      console.log("Audio message:");
      if (state.audio.player) {
        state.audio.player.play(message.data);
      }
      break;

    case MultimodalLiveResponseType.INPUT_TRANSCRIPTION:
      console.log("Input transcription:", message.data);
      if (!message.data.finished) {
        addMessage(message.data.text, "user-transcript", (append = true));
      }
      break;

    case MultimodalLiveResponseType.OUTPUT_TRANSCRIPTION:
      console.log("Output transcription:", message.data);
      if (!message.data.finished) {
        addMessage(message.data.text, "assistant", (append = true));
      }
      break;

    case MultimodalLiveResponseType.SETUP_COMPLETE:
      console.log("Setup complete:", message.data);
      addMessage("Ready!", "system");

      // Display the setup JSON
      if (state.client && state.client.lastSetupMessage) {
        elements.setupJsonDisplay.textContent = JSON.stringify(
          state.client.lastSetupMessage,
          null,
          2
        );
        elements.setupJsonSection.style.display = "block";
      }
      break;

    case MultimodalLiveResponseType.TOOL_CALL:
      console.log("🛠️ Tool call received: ", message.data);
      const functionCalls = message.data.functionCalls;
      for (let index = 0; index < functionCalls.length; index++) {
        const functionCall = functionCalls[index];
        const functionName = functionCall.name;
        const parameters = functionCall.args;
        console.log(
          `Calling function ${functionName} with parameters: ${JSON.stringify(
            parameters
          )}`
        );
        state.client.callFunction(functionName, parameters);
      }
      break;

    case MultimodalLiveResponseType.TURN_COMPLETE:
      console.log("Turn complete:", message.data);
      updateStatus("debugInfo", "Turn complete");
      break;

    case MultimodalLiveResponseType.INTERRUPTED:
      console.log("Interrupted");
      addMessage("[Interrupted]", "system");
      if (state.audio.player) state.audio.player.interrupt();
      break;
  }
}

// Connection handlers
function handleOpen() {
  updateStatus("connectionStatus", "Connected");
}

function handleClose() {
  updateStatus("connectionStatus", "Disconnected");
  disconnect();
}

function handleError(error) {
  console.error("Error:", error);
  updateStatus("connectionStatus", "Error: " + error);
  updateStatus("debugInfo", "Error: " + error);
}

// Toggle audio
async function toggleAudio() {
  if (!state.audio.isStreaming) {
    try {
      // Initialize streamer if needed
      if (!state.audio.streamer && state.client) {
        state.audio.streamer = new AudioStreamer(state.client);
      }

      if (state.audio.streamer) {
        // Get selected microphone device ID
        const selectedMicId = elements.micSelect.value;
        await state.audio.streamer.start(selectedMicId);
        state.audio.isStreaming = true;
        elements.startAudioBtn.textContent = "Stop Audio";
        addMessage("[Microphone on]", "system");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    } catch (error) {
      addMessage("[Audio error: " + error.message + "]", "system");
    }
  } else {
    if (state.audio.streamer) state.audio.streamer.stop();
    state.audio.isStreaming = false;
    elements.startAudioBtn.textContent = "Start Audio";
    addMessage("[Microphone off]", "system");
  }
}

// Toggle video
async function toggleVideo() {
  if (!state.video.isStreaming) {
    try {
      // Initialize streamer if needed
      if (!state.video.streamer && state.client) {
        state.video.streamer = new VideoStreamer(state.client);
      }

      if (state.video.streamer) {
        // Get selected camera device ID
        const selectedCameraId = elements.cameraSelect.value;
        const video = await state.video.streamer.start({
          fps: 1,
          width: 640,
          height: 480,
          deviceId: selectedCameraId || null,
        });
        state.video.isStreaming = true;

        elements.videoPreview.srcObject = video.srcObject;
        elements.videoPreview.hidden = false;
        elements.startVideoBtn.textContent = "Stop Video";
        addMessage("[Camera on]", "system");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    } catch (error) {
      addMessage("[Video error: " + error.message + "]", "system");
    }
  } else {
    if (state.video.streamer) state.video.streamer.stop();
    state.video.isStreaming = false;

    elements.videoPreview.srcObject = null;
    elements.videoPreview.hidden = true;
    elements.startVideoBtn.textContent = "Start Video";
    addMessage("[Camera off]", "system");
  }
}

// Toggle screen
async function toggleScreen() {
  if (!state.screen.isSharing) {
    try {
      // Initialize capture if needed
      if (!state.screen.capture && state.client) {
        state.screen.capture = new ScreenCapture(state.client);
      }

      if (state.screen.capture) {
        const video = await state.screen.capture.start({ fps: 0.5 });
        state.screen.isSharing = true;

        // Show screen preview in the same video element
        elements.videoPreview.srcObject = video.srcObject;
        elements.videoPreview.hidden = false;
        elements.startScreenBtn.textContent = "Stop Sharing";
        addMessage("[Screen sharing on]", "system");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    } catch (error) {
      addMessage("[Screen share error: " + error.message + "]", "system");
    }
  } else {
    if (state.screen.capture) state.screen.capture.stop();
    state.screen.isSharing = false;

    // Hide preview if not using camera
    if (!state.video.isStreaming) {
      elements.videoPreview.srcObject = null;
      elements.videoPreview.hidden = true;
    }

    elements.startScreenBtn.textContent = "Share Screen";
    addMessage("[Screen sharing off]", "system");
  }
}

// Send message
function sendMessage() {
  const message = elements.chatInput.value.trim();
  if (!message) return;

  if (state.client) {
    addMessage(message, "user");
    state.client.sendTextMessage(message);
    elements.chatInput.value = "";
  } else {
    addMessage("[Connect to Gemini first]", "system");
  }
}

// Add message to chat
function addMessage(text, type, append = false) {
  // Get all div children (messages)
  const messages = elements.chatContainer.querySelectorAll("div");
  const lastMessage = messages[messages.length - 1];

  // Check if we should append to the last message
  if (append && lastMessage && lastMessage.className === type) {
    // Append to existing message of the same type
    lastMessage.textContent += text;
  } else {
    // Create new message
    const message = createMessage(text, type);
    elements.chatContainer.appendChild(message);
  }

  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// Update volume
function updateVolume() {
  const value = elements.volume.value;
  const volume = value / 100;
  if (state.audio.player) {
    state.audio.player.setVolume(volume);
  }
  updateStatus("volumeValue", value + "%");
}

// Update temperature display
function updateTemperature() {
  const value = elements.temperature.value;
  updateStatus("temperatureValue", value);
}

// Event listeners
function initEventListeners() {
  elements.connectBtn.addEventListener("click", connect);
  elements.disconnectBtn.addEventListener("click", disconnect);
  elements.startAudioBtn.addEventListener("click", toggleAudio);
  elements.startVideoBtn.addEventListener("click", toggleVideo);
  elements.startScreenBtn.addEventListener("click", toggleScreen);
  elements.sendBtn.addEventListener("click", sendMessage);
  elements.volume.addEventListener("input", updateVolume);
  elements.temperature.addEventListener("input", updateTemperature);

  elements.chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
}

// Initialize
window.addEventListener("DOMContentLoaded", () => {
  initDOM();
  initEventListeners();
  populateMediaDevices();
  updateStatus("debugInfo", "Application initialized");
});
