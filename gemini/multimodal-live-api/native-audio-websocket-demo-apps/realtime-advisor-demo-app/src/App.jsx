import { useState, useRef } from "react";
import LiveAPIDemo from "./components/LiveAPIDemo";
import "./App.css";

function App() {
  const [advisorMode, setAdvisorMode] = useState("silent");
  const [isConnected, setIsConnected] = useState(false);
  const [isAudioOn, setIsAudioOn] = useState(false);
  const liveApiRef = useRef(null);

  const [knowledge, setKnowledge] = useState(
    "Business Accounting Data:\n" +
      "Q1 Revenue: $1.2M\n" +
      "Q2 Revenue: $1.5M\n" +
      "Q3 Revenue: $1.1M\n" +
      "Q4 Revenue: $1.8M\n" +
      "Total Annual Revenue: $5.6M\n" +
      "Net Profit Margin: 15%\n" +
      "Top Selling Product: Widget X ($2.1M sales)\n" +
      "Employee Count: 45"
  );

  const handleConnectToggle = () => {
    if (isConnected) {
      liveApiRef.current?.disconnect();
    } else {
      liveApiRef.current?.connect();
    }
  };

  const handleAudioToggle = () => {
    liveApiRef.current?.toggleAudio();
  };

  return (
    <div className="App">
      <LiveAPIDemo
        ref={liveApiRef}
        knowledge={knowledge}
        advisorMode={advisorMode}
        onConnectionChange={setIsConnected}
        onAudioStreamChange={setIsAudioOn}
      />
      <div className="main-content">
        <div className="column left-column">
          <div className="onboarding-container">
            <h2 className="column-header">About this Demo</h2>

            <div className="onboarding-step">
              <div className="info-section">
                <h3>Real-time Advisor</h3>
                <p>
                  This demo leverages <strong>Proactive Audio</strong> and{" "}
                  <strong>Function Calling</strong> to solve the problem of a
                  real-time advisor. The model listens and decides when to
                  interject or display information based on the conversation
                  flow.
                </p>
              </div>

              <div className="info-section">
                <h3>Knowledge Injection</h3>
                <p>
                  We inject knowledge directly via{" "}
                  <strong>System Instructions</strong>. In production, this
                  could be enhanced with <strong>RAG</strong>{" "}
                  (Retrieval-Augmented Generation) or by creating custom data
                  connectors using the <strong>Custom Tools</strong> feature to
                  access vast knowledge bases dynamically.
                </p>
              </div>

              <div className="info-section">
                <h3>High Responsiveness</h3>
                <p>
                  We have set the <strong>End of Speech Sensitivity</strong> to
                  "High". This makes the model more likely to catch the end of
                  speech mid-conversation, resulting in snappier interactions.
                </p>
              </div>

              <div className="info-section">
                <h3>Uninterrupted Advice</h3>
                <p>
                  We disabled <strong>Barge-in</strong> (Activity Handling
                  setting) so that the advisor's response is not cut off by the
                  ongoing conversation, ensuring the user hears the full advice.
                </p>
              </div>
            </div>

            <div className="onboarding-step">
              <h3>Setup</h3>
              <p>
                Start <code>server.py</code> locally and specify your Google
                Cloud <strong>Project ID</strong> in the Configuration dropdown
                before connecting.
              </p>
            </div>
          </div>
        </div>

        <div className="column center-column">
          <div className="advisor-panel">
            <h2>Advisor Settings</h2>
            <div className="mode-toggle">
              <button
                className={`mode-btn ${
                  advisorMode === "silent" ? "active" : ""
                }`}
                onClick={() => setAdvisorMode("silent")}
              >
                <div className="mode-title">🤫 Silent Mode</div>
                <div className="mode-desc">
                  "Do NOT speak the answer out loud. Remain silent."
                </div>
              </button>
              <button
                className={`mode-btn ${
                  advisorMode === "outspoken" ? "active" : ""
                }`}
                onClick={() => setAdvisorMode("outspoken")}
              >
                <div className="mode-title">🗣️ Outspoken Mode</div>
                <div className="mode-desc">
                  "Politely interject and speak the answer out loud."
                </div>
              </button>
            </div>
            <p className="section-description">
              Define the expertise of your AI Advisor. Enter any text, data, or
              context below that the advisor should use to answer questions.
            </p>
            <textarea
              className="knowledge-input"
              value={knowledge}
              onChange={(e) => setKnowledge(e.target.value)}
              placeholder="Enter knowledge here..."
            />
          </div>
        </div>

        <div className="column right-column">
          <div className="advisor-panel">
            <h2>Controls</h2>
            <div className="control-buttons">
              <button
                className={`mode-btn ${isConnected ? "active" : ""}`}
                onClick={handleConnectToggle}
              >
                <div className="mode-title">
                  {isConnected ? "🔌 Disconnect" : "🔌 Connect"}
                </div>
              </button>
              <button
                className={`mode-btn ${isAudioOn ? "active" : ""}`}
                onClick={handleAudioToggle}
                disabled={!isConnected}
                style={{ opacity: !isConnected ? 0.5 : 1 }}
              >
                <div className="mode-title">
                  {isAudioOn ? "🛑 Stop Mic" : "🎙️ Start Mic"}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
