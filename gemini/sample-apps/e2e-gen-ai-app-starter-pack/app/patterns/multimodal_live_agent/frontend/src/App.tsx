/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useRef, useState } from "react";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import ControlTray from "./components/control-tray/ControlTray";
import cn from "classnames";

const defaultHost = "localhost:8000";
const defaultUri = `ws://${defaultHost}/`;

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [serverUrl, setServerUrl] = useState<string>(defaultUri);
  const [runId] = useState<string>(crypto.randomUUID());
  const [userId, setUserId] = useState<string>("user1");

  // Feedback state
  const [feedbackScore, setFeedbackScore] = useState<number>(10);
  const [feedbackText, setFeedbackText] = useState<string>("");
  const [sendFeedback, setShowFeedback] = useState(false);

  const submitFeedback = async () => {
    const feedbackUrl = new URL('feedback', serverUrl.replace('ws', 'http')).href;
    
    try {
      const response = await fetch(feedbackUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          score: feedbackScore,
          text: feedbackText,
          run_id: runId,
          user_id: userId,
          log_type: "feedback"
        })
      });
      if (!response.ok) {
        throw new Error(`Failed to submit feedback: Server returned status ${response.status} ${response.statusText}`);
      }

      // Clear feedback after successful submission
      setFeedbackScore(10);
      setFeedbackText("");
      setShowFeedback(false);
      alert("Feedback submitted successfully!");
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert(`Failed to submit feedback:  ${error}`);
    }
  };

  return (
    <div className="App">
      <LiveAPIProvider url={serverUrl} userId={userId}>
        <div className="streaming-console">
          <SidePanel />
          <main>
            <div className="main-app-area">
              <video
                className={cn("stream", {
                  hidden: !videoRef.current || !videoStream,
                })}
                ref={videoRef}
                autoPlay
                playsInline
              />
            </div>
            <ControlTray
              videoRef={videoRef}
              supportsVideo={true}
              onVideoStreamChange={setVideoStream}
            >
            </ControlTray>
            <div className="url-setup" style={{position: 'absolute', top: 0, left: 0, right: 0, pointerEvents: 'auto', zIndex: 1000, padding: '2px', marginBottom: '2px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255, 255, 255, 0.9)'}}>
              <div>
                <label htmlFor="server-url">Server URL:</label>
                <input
                  id="server-url"
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="Enter server URL"
                  style={{
                    cursor: 'text',
                    padding: '4px',
                    margin: '0 4px', 
                    borderRadius: '2px',
                    border: '1px solid #ccc',
                    fontSize: '14px',
                    fontFamily: 'system-ui, -apple-system, sans-serif',
                    width: '200px'
                  }}
                />
                <label htmlFor="user-id">User ID:</label>
                <input
                  id="user-id"
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="Enter user ID"
                  style={{
                    cursor: 'text',
                    padding: '4px',
                    margin: '0 4px', 
                    borderRadius: '2px',
                    border: '1px solid #ccc',
                    fontSize: '14px',
                    fontFamily: 'system-ui, -apple-system, sans-serif',
                    width: '100px'
                  }}
                />
              </div>

              {/* Feedback Button */}
              <button 
                onClick={() => setShowFeedback(!sendFeedback)}
                style={{
                  padding: '5px 10px',
                  margin: '10px',
                  cursor: 'pointer'
                }}
              >
                {sendFeedback ? 'Hide Feedback' : 'Send Feedback'}
              </button>
            </div>

            {/* Feedback Overlay Section */}
            {sendFeedback && (
              <div className="feedback-section" style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                padding: '20px',
                background: 'rgba(255, 255, 255, 0.95)',
                boxShadow: '0 0 10px rgba(0,0,0,0.2)',
                borderRadius: '8px',
                zIndex: 1001,
                minWidth: '300px'
              }}>
                <h3>Provide Feedback</h3>
                <div>
                  <label htmlFor="feedback-score">Score (0-10): </label>
                  <input
                    id="feedback-score"
                    type="number"
                    min="0"
                    max="10"
                    value={feedbackScore}
                    onChange={(e) => setFeedbackScore(Number(e.target.value))}
                    style={{margin: '0 10px'}}
                  />
                </div>
                <div style={{marginTop: '10px'}}>
                  <label htmlFor="feedback-text">Comments: </label>
                  <textarea
                    id="feedback-text"
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    style={{
                      width: '100%',
                      height: '60px',
                      margin: '5px 0'
                    }}
                  />
                </div>
                <button
                  onClick={submitFeedback}
                  style={{
                    padding: '5px 10px',
                    marginTop: '5px',
                    cursor: 'pointer'
                  }}
                >
                  Submit Feedback
                </button>
              </div>
            )}
          </main>
        </div>
      </LiveAPIProvider>
    </div>
  );
}

export default App;
