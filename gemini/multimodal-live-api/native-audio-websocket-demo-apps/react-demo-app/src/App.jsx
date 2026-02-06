import LiveAPIDemo from "./components/LiveAPIDemo";
import "./App.css";

function App() {
  return (
    <div className="App">
      <LiveAPIDemo />
      <div className="main-content">
        <div className="onboarding-container">
          <div className="onboarding-step">
            <h3>Step 1: Configure</h3>
            <p>Start <code>server.py</code> locally, select your settings in the Configuration dropdown, and click the Connect button.</p>
          </div>
          <div className="onboarding-step">
            <h3>Step 2: Media</h3>
            <p>Enable your microphone and camera in the Media dropdown to stream input.</p>
          </div>
          <div className="onboarding-step">
            <h3>Step 3: Chat</h3>
            <p>Use the Chat dropdown to see transcriptions and send text messages.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
