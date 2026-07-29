import React, { useRef, useState, useEffect } from "react";
import LiveAPIDemo from "./components/LiveAPIDemo";
import "./App.css";

function App() {
  const liveAPIRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [audioStreaming, setAudioStreaming] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const videoRef = useRef(null);
  const [selectedPersona, setSelectedPersona] = useState(null);

  const PERSONAS = [
    {
      name: "Wise Wizard",
      emoji: "🧙‍♂️",
      voice: "Fenrir",
      instructions:
        "You are a wise, ancient wizard gaming assistant. Speak in the wispy but wise voice of an ancient wizzard. Call the user 'Traveler'. Be helpful but mysterious.",
    },
    {
      name: "SciFi Robot",
      emoji: "🤖",
      voice: "Kore",
      instructions:
        "You are a futuristic sci-fi space robot gaming assistant. Speak in a robotic voice.  Call the user 'Captain'. Be precise and analytical.",
    },
    {
      name: "Commander",
      emoji: "🫡",
      voice: "Charon",
      instructions:
        "You are a stern military commander gaming assistant. Speak with authority and brevity. Use military terminology. Call the user 'Soldier'. Demand victory.",
    },
  ];

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  const handlePersonaSelect = (persona) => {
    setSelectedPersona(persona);
    if (liveAPIRef.current) {
      liveAPIRef.current.setConfig({
        systemInstructions: persona.instructions,
        voice: persona.voice,
      });
    }
  };

  const handleConnect = () => {
    if (connected) {
      liveAPIRef.current.disconnect();
    } else {
      liveAPIRef.current.connect();
    }
  };

  const handleAudio = () => {
    if (!connected) {
      alert("Please connect to the API first.");
      return;
    }
    liveAPIRef.current.toggleAudio();
  };

  const handleScreen = () => {
    if (!connected) {
      alert("Please connect to the API first.");
      return;
    }
    liveAPIRef.current.toggleScreen();
  };

  return (
    <div className="App">
      <LiveAPIDemo
        ref={liveAPIRef}
        onConnectionChange={setConnected}
        onAudioStreamChange={setAudioStreaming}
        onScreenShareChange={setScreenSharing}
        onPreviewStreamChange={setVideoStream}
      />
      <div className="main-content">
        <div className="onboarding-container">
          <div className="onboarding-step">
            <h3>Gaming Assistant Demo</h3>
            <p>
              This demo uses Gemini Live API to act as a gaming assistant. It
              can see your screen and hear your voice to help you play games.
            </p>
            <ul className="feature-list">
              <li>
                <strong>Multimodal:</strong> Sees your game and hears you
              </li>
              <li>
                <strong>Proactive Audio:</strong> Speaks when it has something
                useful to say
              </li>
              <li>
                <strong>Google Grounding:</strong> Uses real-time info to help
              </li>
              <li>
                <strong>Native Audio:</strong> Engaging, low-latency voice that
                allows for completely custom voices through prompting with
                personas
              </li>
            </ul>
          </div>
          <div className="onboarding-step">
            <h3>Step 1: Configure</h3>
            <p>
              Start <code>server.py</code> locally, add your project ID in the
              Configuration dropdown.
            </p>
          </div>
          <div className="onboarding-step">
            <h3>Step 2: Choose Persona</h3>
            <div className="persona-selector">
              {PERSONAS.map((persona) => (
                <button
                  key={persona.name}
                  className={`persona-button ${
                    selectedPersona?.name === persona.name ? "active" : ""
                  }`}
                  onClick={() => handlePersonaSelect(persona)}
                >
                  <span className="persona-emoji">{persona.emoji}</span>
                  <span className="persona-name">{persona.name}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="control-bar">
            <button
              onClick={handleConnect}
              className={connected ? "active" : ""}
            >
              {connected ? "Disconnect" : "Connect"}
            </button>
            <button
              onClick={handleAudio}
              className={audioStreaming ? "active" : ""}
            >
              {audioStreaming ? "Stop Mic" : "Start Mic"}
            </button>
            <button
              onClick={handleScreen}
              className={screenSharing ? "active" : ""}
            >
              {screenSharing ? "Stop Screen Share" : "Share Screen"}
            </button>
          </div>
        </div>
        <div className="video-container">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`main-video-preview ${videoStream ? "" : "hidden"}`}
          />
          {!videoStream && (
            <div className="video-placeholder">Waiting for screen share</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
