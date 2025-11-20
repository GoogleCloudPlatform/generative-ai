import React, {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import { GeminiLiveAPI, MultimodalLiveResponseType } from "../utils/gemini-api";
import {
  AudioStreamer,
  VideoStreamer,
  ScreenCapture,
  AudioPlayer,
} from "../utils/media-utils";
import { ShowModalDialogTool, AddCSSStyleTool } from "../utils/tools";
import "./LiveAPIDemo.css";

const LiveAPIDemo = forwardRef(
  (
    { knowledge, advisorMode, onConnectionChange, onAudioStreamChange },
    ref
  ) => {
    // Connection State
    const [connected, setConnected] = useState(false);
    const [setupJson, setSetupJson] = useState(null);

    // Modal State
    const [modalVisible, setModalVisible] = useState(false);
    const [modalContent, setModalContent] = useState({
      title: "",
      message: "",
    });

    // Configuration State
    const [proxyUrl, setProxyUrl] = useState(
      localStorage.getItem("proxyUrl") || "ws://localhost:8080"
    );
    const [projectId, setProjectId] = useState(
      localStorage.getItem("projectId")
    );
    const [model, setModel] = useState(
      localStorage.getItem("model") ||
        "gemini-live-2.5-flash-preview-native-audio-09-2025"
    );

    useEffect(() => {
      localStorage.setItem("proxyUrl", proxyUrl);
    }, [proxyUrl]);

    useEffect(() => {
      localStorage.setItem("projectId", projectId);
    }, [projectId]);

    useEffect(() => {
      localStorage.setItem("model", model);
    }, [model]);

    // Calculate system instructions directly from props
    const systemInstructions = `You are listening to a conversation. Your goal is to help the user by providing information from the provided knowledge base.
    
Knowledge Base:
${knowledge}

Instructions:
1. Listen to the conversation.
2. If you hear a question that can be answered by the knowledge base:
   ${
     advisorMode === "silent"
       ? 'a. Call the "show_modal" tool with the answer.\n   b. Do NOT speak the answer out loud. Remain silent.'
       : 'a. First, politely interject and speak the answer out loud.\n   b. Then, call the "show_modal" tool with the answer.\n   IMPORTANT: You must perform BOTH actions (Speak AND Show Modal).'
   }
3. If the question cannot be answered by the knowledge base, do NOT respond.
4. Remain silent otherwise.
`;

    const [voice, setVoice] = useState("Puck");

    const [temperature, setTemperature] = useState(1.0);
    const [enableProactiveAudio, setEnableProactiveAudio] = useState(true);
    const [enableGrounding, setEnableGrounding] = useState(false);
    const [enableAffectiveDialog, setEnableAffectiveDialog] = useState(true);
    const [enableAlertTool, setEnableAlertTool] = useState(true);
    const [enableCssStyleTool, setEnableCssStyleTool] = useState(false);
    const [enableInputTranscription, setEnableInputTranscription] =
      useState(true);
    const [enableOutputTranscription, setEnableOutputTranscription] =
      useState(true);

    // Activity Detection State
    const [disableActivityDetection, setDisableActivityDetection] =
      useState(false);
    const [silenceDuration, setSilenceDuration] = useState(0);
    const [prefixPadding, setPrefixPadding] = useState(500);
    const [endSpeechSensitivity, setEndSpeechSensitivity] = useState(
      "END_SENSITIVITY_HIGH"
    );
    const [startSpeechSensitivity, setStartSpeechSensitivity] = useState(
      "START_SENSITIVITY_UNSPECIFIED"
    );
    const [activityHandling, setActivityHandling] = useState("NO_INTERRUPTION");

    // Media State
    const [audioStreaming, setAudioStreaming] = useState(false);
    const [videoStreaming, setVideoStreaming] = useState(false);
    const [screenSharing, setScreenSharing] = useState(false);
    const [volume, setVolume] = useState(80);
    const [audioInputDevices, setAudioInputDevices] = useState([]);
    const [videoInputDevices, setVideoInputDevices] = useState([]);
    const [selectedMic, setSelectedMic] = useState("");
    const [selectedCamera, setSelectedCamera] = useState("");

    // Chat State
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");

    // Refs
    const clientRef = useRef(null);
    const audioStreamerRef = useRef(null);
    const videoStreamerRef = useRef(null);
    const screenCaptureRef = useRef(null);
    const audioPlayerRef = useRef(null);
    const videoPreviewRef = useRef(null);
    const chatContainerRef = useRef(null);

    // Initialize Media Devices
    useEffect(() => {
      const getDevices = async () => {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          setAudioInputDevices(
            devices.filter((device) => device.kind === "audioinput")
          );
          setVideoInputDevices(
            devices.filter((device) => device.kind === "videoinput")
          );
        } catch (error) {
          console.error("Error enumerating devices:", error);
        }
      };
      getDevices();
    }, []);

    // Scroll to bottom of chat
    useEffect(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop =
          chatContainerRef.current.scrollHeight;
      }
    }, [chatMessages]);

    const addMessage = (text, type, append = false) => {
      setChatMessages((prev) => {
        if (append && prev.length > 0 && prev[prev.length - 1].type === type) {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].text += text;
          return newMessages;
        }
        return [...prev, { text, type }];
      });
    };

    const handleMessage = (message) => {
      switch (message.type) {
        case MultimodalLiveResponseType.TEXT:
          addMessage(message.data, "assistant");
          break;
        case MultimodalLiveResponseType.AUDIO:
          if (audioPlayerRef.current) {
            audioPlayerRef.current.play(message.data);
          }
          break;
        case MultimodalLiveResponseType.INPUT_TRANSCRIPTION:
          if (!message.data.finished) {
            addMessage(message.data.text, "user-transcript", true);
          }
          break;
        case MultimodalLiveResponseType.OUTPUT_TRANSCRIPTION:
          if (!message.data.finished) {
            addMessage(message.data.text, "assistant", true);
          }
          break;
        case MultimodalLiveResponseType.SETUP_COMPLETE:
          addMessage("Ready!", "system");
          if (clientRef.current && clientRef.current.lastSetupMessage) {
            setSetupJson(clientRef.current.lastSetupMessage);
          }
          break;
        case MultimodalLiveResponseType.TOOL_CALL: {
          const functionCalls = message.data.functionCalls;
          functionCalls.forEach((functionCall) => {
            const { name, args } = functionCall;
            console.log(
              `Calling function ${name} with parameters: ${JSON.stringify(
                args
              )}`
            );
            clientRef.current.callFunction(name, args);
          });
          break;
        }
        case MultimodalLiveResponseType.TURN_COMPLETE:
          // Turn complete
          break;
        case MultimodalLiveResponseType.INTERRUPTED:
          addMessage("[Interrupted]", "system");
          if (audioPlayerRef.current) {
            audioPlayerRef.current.interrupt();
          }
          break;
        default:
          break;
      }
    };

    const disconnect = () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }

      if (audioStreamerRef.current) {
        audioStreamerRef.current.stop();
        audioStreamerRef.current = null;
      }
      if (videoStreamerRef.current) {
        videoStreamerRef.current.stop();
        videoStreamerRef.current = null;
      }
      if (screenCaptureRef.current) {
        screenCaptureRef.current.stop();
        screenCaptureRef.current = null;
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.destroy();
        audioPlayerRef.current = null;
      }

      setConnected(false);
      setAudioStreaming(false);
      setVideoStreaming(false);
      setScreenSharing(false);

      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = null;
        videoPreviewRef.current.hidden = true;
      }
    };

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        disconnect();
      };
    }, []);

    const connect = async () => {
      if (!proxyUrl && !projectId) {
        alert("Please provide either a Proxy URL and Project ID");
        return;
      }

      try {
        clientRef.current = new GeminiLiveAPI(proxyUrl, projectId, model);

        clientRef.current.systemInstructions = systemInstructions;
        clientRef.current.inputAudioTranscription = enableInputTranscription;
        clientRef.current.outputAudioTranscription = enableOutputTranscription;
        clientRef.current.googleGrounding = enableGrounding;
        clientRef.current.enableAffectiveDialog = enableAffectiveDialog;
        clientRef.current.responseModalities = ["AUDIO"];
        clientRef.current.voiceName = voice;
        clientRef.current.temperature = parseFloat(temperature);
        clientRef.current.proactivity = {
          proactiveAudio: enableProactiveAudio,
        };
        clientRef.current.automaticActivityDetection = {
          disabled: disableActivityDetection,
          silence_duration_ms: parseInt(silenceDuration),
          prefix_padding_ms: parseInt(prefixPadding),
          end_of_speech_sensitivity: endSpeechSensitivity,
          start_of_speech_sensitivity: startSpeechSensitivity,
        };

        clientRef.current.activityHandling = activityHandling;

        if (!enableGrounding) {
          if (enableAlertTool) {
            clientRef.current.addFunction(
              new ShowModalDialogTool((message, title) => {
                setModalContent({ title, message });
                setModalVisible(true);
              })
            );
          }
          if (enableCssStyleTool) {
            clientRef.current.addFunction(new AddCSSStyleTool());
          }
        }

        clientRef.current.onReceiveResponse = handleMessage;
        clientRef.current.onErrorMessage = (error) => {
          console.error("Error:", error);
        };
        clientRef.current.onConnectionStarted = () => {
          setConnected(true);
        };
        clientRef.current.onClose = () => {
          setConnected(false);
          disconnect();
        };

        await clientRef.current.connect();

        audioStreamerRef.current = new AudioStreamer(clientRef.current);
        videoStreamerRef.current = new VideoStreamer(clientRef.current);
        screenCaptureRef.current = new ScreenCapture(clientRef.current);
        audioPlayerRef.current = new AudioPlayer();
        await audioPlayerRef.current.init();
        audioPlayerRef.current.setVolume(volume / 100);
      } catch (error) {
        console.error("Connection failed:", error);
      }
    };

    const toggleAudio = async () => {
      if (!audioStreaming) {
        try {
          if (!audioStreamerRef.current && clientRef.current) {
            audioStreamerRef.current = new AudioStreamer(clientRef.current);
          }

          if (audioStreamerRef.current) {
            await audioStreamerRef.current.start(selectedMic);
            setAudioStreaming(true);
            addMessage("[Microphone on]", "system");
          } else {
            addMessage("[Connect to Gemini first]", "system");
          }
        } catch (error) {
          addMessage("[Audio error: " + error.message + "]", "system");
        }
      } else {
        if (audioStreamerRef.current) audioStreamerRef.current.stop();
        setAudioStreaming(false);
        addMessage("[Microphone off]", "system");
      }
    };

    const toggleVideo = async () => {
      if (!videoStreaming) {
        try {
          if (!videoStreamerRef.current && clientRef.current) {
            videoStreamerRef.current = new VideoStreamer(clientRef.current);
          }

          if (videoStreamerRef.current) {
            const video = await videoStreamerRef.current.start({
              deviceId: selectedCamera,
            });
            setVideoStreaming(true);
            if (videoPreviewRef.current) {
              videoPreviewRef.current.srcObject = video.srcObject;
              videoPreviewRef.current.hidden = false;
            }
            addMessage("[Camera on]", "system");
          } else {
            addMessage("[Connect to Gemini first]", "system");
          }
        } catch (error) {
          addMessage("[Video error: " + error.message + "]", "system");
        }
      } else {
        if (videoStreamerRef.current) videoStreamerRef.current.stop();
        setVideoStreaming(false);
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
          videoPreviewRef.current.hidden = true;
        }
        addMessage("[Camera off]", "system");
      }
    };

    const toggleScreen = async () => {
      if (!screenSharing) {
        try {
          if (!screenCaptureRef.current && clientRef.current) {
            screenCaptureRef.current = new ScreenCapture(clientRef.current);
          }

          if (screenCaptureRef.current) {
            const video = await screenCaptureRef.current.start();
            setScreenSharing(true);
            if (videoPreviewRef.current) {
              videoPreviewRef.current.srcObject = video.srcObject;
              videoPreviewRef.current.hidden = false;
            }
            addMessage("[Screen sharing on]", "system");
          } else {
            addMessage("[Connect to Gemini first]", "system");
          }
        } catch (error) {
          addMessage("[Screen share error: " + error.message + "]", "system");
        }
      } else {
        if (screenCaptureRef.current) screenCaptureRef.current.stop();
        setScreenSharing(false);
        if (!videoStreaming && videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
          videoPreviewRef.current.hidden = true;
        }
        addMessage("[Screen sharing off]", "system");
      }
    };

    const sendMessage = () => {
      if (!chatInput.trim()) return;

      if (clientRef.current) {
        addMessage(chatInput, "user");
        clientRef.current.sendTextMessage(chatInput);
        setChatInput("");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    };

    const handleVolumeChange = (e) => {
      const newVolume = e.target.value;
      setVolume(newVolume);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.setVolume(newVolume / 100);
      }
    };

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      connect,
      disconnect,
      toggleAudio,
    }));

    // Notify parent of state changes
    useEffect(() => {
      onConnectionChange?.(connected);
    }, [connected, onConnectionChange]);

    useEffect(() => {
      onAudioStreamChange?.(audioStreaming);
    }, [audioStreaming, onAudioStreamChange]);

    return (
      <div className="live-api-demo">
        <div className="toolbar">
          <div className="toolbar-left">
            <h1>Real-time Advisor</h1>
            <span className="powered-by">Powered by Gemini Live API</span>
          </div>
          <div className="toolbar-center">
            <div className="dropdown">
              <button className="dropbtn">Configuration ▾</button>
              <div className="dropdown-content config-dropdown">
                {/* API Configuration Section */}
                <div className="control-group">
                  <h3>Connection Settings</h3>
                  <div className="input-group">
                    <label>Proxy WebSocket URL:</label>
                    <input
                      type="text"
                      value={proxyUrl}
                      onChange={(e) => setProxyUrl(e.target.value)}
                      placeholder="ws://localhost:8080"
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>Project ID:</label>
                    <input
                      type="text"
                      value={projectId}
                      onChange={(e) => setProjectId(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>Model ID:</label>
                    <input
                      type="text"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                </div>

                <div className="control-group">
                  <h3>Gemini Behavior</h3>
                  <div className="input-group">
                    <label>System Instructions:</label>
                    <textarea
                      rows="3"
                      value={systemInstructions}
                      readOnly
                      disabled={true}
                    />
                  </div>
                  <div className="input-group">
                    <label>Voice:</label>
                    <select
                      value={voice}
                      onChange={(e) => setVoice(e.target.value)}
                      disabled={connected}
                    >
                      <option value="Puck">Puck (Default)</option>
                      <option value="Charon">Charon</option>
                      <option value="Kore">Kore</option>
                      <option value="Fenrir">Fenrir</option>
                      <option value="Aoede">Aoede</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Temperature: {temperature}</label>
                    <input
                      type="range"
                      min="0.1"
                      max="2.0"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(e.target.value)}
                      disabled={connected}
                    />
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableProactiveAudio}
                      onChange={(e) =>
                        setEnableProactiveAudio(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>Enable proactive audio</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableGrounding}
                      onChange={(e) => setEnableGrounding(e.target.checked)}
                      disabled={connected}
                    />
                    <label>Enable Google grounding</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableAffectiveDialog}
                      onChange={(e) =>
                        setEnableAffectiveDialog(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>Enable affective dialog</label>
                  </div>
                </div>

                <div className="control-group">
                  <h3>Custom Tools</h3>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableAlertTool}
                      onChange={(e) => setEnableAlertTool(e.target.checked)}
                      disabled={connected || enableGrounding}
                    />
                    <label>Show Modal Dialog</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableCssStyleTool}
                      onChange={(e) => setEnableCssStyleTool(e.target.checked)}
                      disabled={connected || enableGrounding}
                    />
                    <label>Add CSS Style</label>
                  </div>
                </div>

                <div className="control-group">
                  <h3>Transcription Settings</h3>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableInputTranscription}
                      onChange={(e) =>
                        setEnableInputTranscription(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>Enable input transcription</label>
                  </div>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={enableOutputTranscription}
                      onChange={(e) =>
                        setEnableOutputTranscription(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>Enable output transcription</label>
                  </div>
                </div>

                <div className="control-group">
                  <h3>Activity Detection Settings</h3>
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      checked={disableActivityDetection}
                      onChange={(e) =>
                        setDisableActivityDetection(e.target.checked)
                      }
                      disabled={connected}
                    />
                    <label>Disable automatic activity detection</label>
                  </div>
                  <div className="input-group">
                    <label>Silence duration (ms):</label>
                    <input
                      type="number"
                      value={silenceDuration}
                      onChange={(e) => setSilenceDuration(e.target.value)}
                      min="500"
                      max="10000"
                      step="100"
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>Prefix padding (ms):</label>
                    <input
                      type="number"
                      value={prefixPadding}
                      onChange={(e) => setPrefixPadding(e.target.value)}
                      min="0"
                      max="2000"
                      step="100"
                      disabled={connected}
                    />
                  </div>
                  <div className="input-group">
                    <label>End of speech sensitivity:</label>
                    <select
                      value={endSpeechSensitivity}
                      onChange={(e) => setEndSpeechSensitivity(e.target.value)}
                      disabled={connected}
                    >
                      <option value="END_SENSITIVITY_UNSPECIFIED">
                        Default
                      </option>
                      <option value="END_SENSITIVITY_HIGH">High</option>
                      <option value="END_SENSITIVITY_LOW">Low</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Start of speech sensitivity:</label>
                    <select
                      value={startSpeechSensitivity}
                      onChange={(e) =>
                        setStartSpeechSensitivity(e.target.value)
                      }
                      disabled={connected}
                    >
                      <option value="START_SENSITIVITY_UNSPECIFIED">
                        Default
                      </option>
                      <option value="START_SENSITIVITY_HIGH">High</option>
                      <option value="START_SENSITIVITY_LOW">Low</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Activity Handling:</label>
                    <select
                      value={activityHandling}
                      onChange={(e) => setActivityHandling(e.target.value)}
                      disabled={connected}
                    >
                      <option value="ACTIVITY_HANDLING_UNSPECIFIED">
                        Default (Interrupts)
                      </option>
                      <option value="START_OF_ACTIVITY_INTERRUPTS">
                        Interrupt (Barge-in)
                      </option>
                      <option value="NO_INTERRUPTION">No Interruption</option>
                    </select>
                  </div>
                </div>

                {setupJson && (
                  <div className="control-group">
                    <h3>Setup Message JSON</h3>
                    <pre className="setup-json-display">
                      {JSON.stringify(setupJson, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={connected ? disconnect : connect}
              className={connected ? "disconnect" : "active"}
            >
              {connected ? "Disconnect" : "Connect"}
            </button>

            <div className="dropdown">
              <button className="dropbtn">Media ▾</button>
              <div className="dropdown-content media-dropdown">
                {/* Media Streaming Section */}
                <div className="control-group">
                  <div className="input-group">
                    <label>Microphone:</label>
                    <select
                      value={selectedMic}
                      onChange={(e) => setSelectedMic(e.target.value)}
                    >
                      <option value="">Default Microphone</option>
                      {audioInputDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Microphone ${device.deviceId}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Camera:</label>
                    <select
                      value={selectedCamera}
                      onChange={(e) => setSelectedCamera(e.target.value)}
                    >
                      <option value="">Default Camera</option>
                      {videoInputDevices.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || `Camera ${device.deviceId}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="button-group-vertical">
                    <button
                      onClick={toggleAudio}
                      className={audioStreaming ? "active" : ""}
                    >
                      {audioStreaming ? "Stop Audio" : "Start Audio"}
                    </button>
                    <button
                      onClick={toggleVideo}
                      className={videoStreaming ? "active" : ""}
                    >
                      {videoStreaming ? "Stop Video" : "Start Video"}
                    </button>
                    <button
                      onClick={toggleScreen}
                      className={screenSharing ? "active" : ""}
                    >
                      {screenSharing ? "Stop Sharing" : "Share Screen"}
                    </button>
                  </div>

                  <div className="input-group">
                    <label>Output volume: {volume}%</label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={volume}
                      onChange={handleVolumeChange}
                    />
                  </div>

                  <video
                    ref={videoPreviewRef}
                    autoPlay
                    playsInline
                    muted
                    hidden
                    className="video-preview"
                  />
                </div>
              </div>
            </div>

            <div className="dropdown">
              <button className="dropbtn">Chat ▾</button>
              <div className="dropdown-content chat-dropdown">
                {/* Chat Section */}
                <div className="chat-container" ref={chatContainerRef}>
                  {chatMessages.length === 0 && (
                    <div>Connect to Gemini to start chatting</div>
                  )}
                  {chatMessages.map((msg, index) => (
                    <div key={index} className={`message ${msg.type}`}>
                      {msg.text}
                    </div>
                  ))}
                </div>
                <div className="chat-input-area">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Type a message..."
                  />
                  <button onClick={sendMessage}>Send</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Dialog */}
        {modalVisible && (
          <div className="modal-overlay">
            <div className="modal-content">
              {modalContent.title && <h2>{modalContent.title}</h2>}
              <p>{modalContent.message}</p>
              <button onClick={() => setModalVisible(false)}>Close</button>
            </div>
          </div>
        )}
      </div>
    );
  }
);

export default LiveAPIDemo;
