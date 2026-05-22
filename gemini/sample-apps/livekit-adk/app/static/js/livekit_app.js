/**
 * Copyright 2026 Google LLC
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

// LiveKit application logic
const { Room, RoomEvent } = LivekitClient;

const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const startAudioButton = document.getElementById('startAudioButton');
const stopAudioButton = document.getElementById('stopAudioButton');
const consoleContent = document.getElementById('consoleContent');
const messagesDiv = document.getElementById('messages');

let room;

function log(message) {
    const div = document.createElement('div');
    div.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
    consoleContent.appendChild(div);
    consoleContent.scrollTop = consoleContent.scrollHeight;
}

let lastSender = null;
let lastBubbleText = null;

function appendMessage(sender, text) {
    const senderType = (sender.toLowerCase() === 'you') ? 'user' : 'agent';
    
    if (lastSender === senderType && lastBubbleText) {
        // Append text to the existing consolidated block
        const currentText = lastBubbleText.textContent;
        if (currentText.length > 0 && !currentText.endsWith(' ') && !text.startsWith(' ')) {
            lastBubbleText.textContent += ' ' + text;
        } else {
            lastBubbleText.textContent += text;
        }
    } else {
        // Create new styled chat bubble
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${senderType}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'bubble';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'bubble-text';
        textDiv.textContent = text;
        
        bubbleDiv.appendChild(textDiv);
        msgDiv.appendChild(bubbleDiv);
        messagesDiv.appendChild(msgDiv);
        
        lastSender = senderType;
        lastBubbleText = textDiv;
    }
    
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function connect() {
    log("Fetching token...");
    statusText.textContent = "Fetching token...";
    
    const userId = "user-" + Math.random().toString(36).substring(7);
    const sessionId = "session-" + Math.random().toString(36).substring(7);
    
    try {
        const response = await fetch(`/token?user_id=${userId}&session_id=${sessionId}`);
        const data = await response.json();
        
        if (data.error) {
            log(`Error fetching token: ${data.error}`);
            statusText.textContent = "Error";
            return;
        }
        
        log("Connecting to LiveKit room...");
        statusText.textContent = "Connecting...";
        
        // Use imported Room class
        room = new Room();
        
        room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
            log(`Subscribed to track ${track.kind} from ${participant.identity}`);
            if (track.kind === 'audio') {
                // Attach audio element to play sound
                const element = track.attach();
                document.body.appendChild(element);
            }
        });
        
        room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
            try {
                const textData = new TextDecoder().decode(payload);
                const msg = JSON.parse(textData);
                if (msg.sender && msg.text) {
                    appendMessage(msg.sender, msg.text);
                }
            } catch (e) {
                log(`Received data error: ${e}`);
            }
        });
        
        room.on(RoomEvent.Disconnected, () => {
            log("Disconnected from room");
            statusIndicator.style.backgroundColor = "red";
            statusText.textContent = "Disconnected";
            startAudioButton.style.display = "inline-block";
            stopAudioButton.style.display = "none";
        });
        
        await room.connect(data.url, data.token);
        
        log("Connected to room!");
        statusIndicator.style.backgroundColor = "green";
        statusText.textContent = "Connected";
        startAudioButton.style.display = "none";
        stopAudioButton.style.display = "inline-block";
        
        // Publish microphone
        log("Publishing microphone...");
        await room.localParticipant.setMicrophoneEnabled(true);
        log("Microphone published!");
        
    } catch (error) {
        log(`Connection failed: ${error}`);
        statusText.textContent = "Failed";
    }
}

async function disconnect() {
    if (room) {
        log("Disconnecting...");
        await room.disconnect();
    }
}

startAudioButton.addEventListener('click', connect);
stopAudioButton.addEventListener('click', disconnect);
document.getElementById('clearConsole').addEventListener('click', () => {
    consoleContent.innerHTML = '';
});
