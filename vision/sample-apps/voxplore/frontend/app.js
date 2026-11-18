/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

document.addEventListener('DOMContentLoaded', () => {
    const statusBadge = document.getElementById('status-badge');
    const connectBtn = document.getElementById('connect-btn');
    const disconnectBtn = document.getElementById('disconnect-btn');
    const micBtn = document.getElementById('mic-btn');
    const cameraBtn = document.getElementById('camera-btn');
    const screenBtn = document.getElementById('screen-btn');
    const paperBtn = document.getElementById('paper-btn');
    const paperFile = document.getElementById('paper-file');
    const inputPreview = document.getElementById('input-preview');
    const tutorName = document.getElementById('tutor-name');
    const avatarSelect = document.getElementById('avatar-select');
    const voiceSelect = document.getElementById('voice-select');

    const avatarImage = document.getElementById('avatar-image');
    const avatarCanvas = document.getElementById('avatar-canvas');
    const avatarPlaceholder = document.getElementById('avatar-placeholder');
    const avatarStatus = document.getElementById('avatar-status');

    function showPlaceholder(connecting) {
        avatarPlaceholder.style.display = 'flex';
        avatarPlaceholder.querySelector('.spinner').style.display = connecting ? 'block' : 'none';
        avatarPlaceholder.querySelector('.placeholder-icon').style.display = connecting ? 'none' : 'block';
        avatarStatus.textContent = connecting ? 'Connecting to your avatar...' : 'Click Connect to start';
    }
    const avatarVideo = document.getElementById('avatar-video');
    const chatLog = document.getElementById('chat-log');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const resetBtn = document.getElementById('reset-btn');
    const featuredSourceBtn = document.getElementById('featured-source-btn');
    const activityPanel = document.getElementById('activity-panel');
    const activityList = document.getElementById('activity-list');

    // Artifacts UI elements
    const appContainer = document.querySelector('.app-container');
    const artifactsToggleBtn = document.getElementById('artifacts-toggle-btn');
    const artifactsBadgeCount = document.getElementById('artifacts-badge-count');
    const artifactsPane = document.getElementById('artifacts-pane');
    const artifactsPaneCount = document.getElementById('artifacts-pane-count');
    const artifactsCloseBtn = document.getElementById('artifacts-close-btn');
    const artifactsExpandBtn = document.getElementById('artifacts-expand-btn');
    const artifactsEmpty = document.getElementById('artifacts-empty');
    const artifactsContent = document.getElementById('artifacts-content');
    const featuredMediaWrapper = document.getElementById('featured-media-wrapper');
    const featuredTypePill = document.getElementById('featured-type-pill');
    const featuredModelPill = document.getElementById('featured-model-pill');
    const featuredTime = document.getElementById('featured-time');
    const featuredPrompt = document.getElementById('featured-prompt');
    const featuredDownloadBtn = document.getElementById('featured-download-btn');
    const featuredFullscreenBtn = document.getElementById('featured-fullscreen-btn');
    const featuredCopyBtn = document.getElementById('featured-copy-btn');
    const featuredCopyText = document.getElementById('featured-copy-text');
    const artifactsGalleryStrip = document.getElementById('artifacts-gallery-strip');

    // Lightbox modal elements
    const mediaLightbox = document.getElementById('media-lightbox');
    const lightboxBackdrop = document.getElementById('lightbox-backdrop');
    const lightboxCloseBtn = document.getElementById('lightbox-close-btn');
    const lightboxContent = document.getElementById('lightbox-content');
    const lightboxCaption = document.getElementById('lightbox-caption');

    // Size the avatar box to the stream so the frame is never cropped
    function fitAvatarContainer() {
        if (!avatarVideo.videoWidth || !avatarVideo.videoHeight) return;
        const container = avatarVideo.parentElement;
        container.style.aspectRatio = `${avatarVideo.videoWidth} / ${avatarVideo.videoHeight}`;
        console.log(`Avatar stream ${avatarVideo.videoWidth}x${avatarVideo.videoHeight}`);
    }
    avatarVideo.addEventListener('loadedmetadata', fitAvatarContainer);
    avatarVideo.addEventListener('resize', fitAvatarContainer);
    avatarVideo.addEventListener('canplay', () => {
        if (avatarVideo.paused && sourceBuffer && !sourceBuffer.updating && avatarVideo.readyState >= 3) {
            avatarVideo.play().catch(() => {});
        }
    });
    avatarVideo.addEventListener('seeked', () => {
        if (avatarVideo.paused && avatarVideo.readyState >= 3) {
            avatarVideo.play().catch(() => {});
        }
    });


    let socket = null;

    // High-Fidelity Audio Streaming & Lip-Sync Alignment
    const AUDIO_SAMPLE_RATE = 24000;
    // Delay audio playback by ~220ms when starting a turn:
    // 1) Buffers initial chunks to eliminate buffer underruns & crackle from network/video jitter
    // 2) Matches the ~200ms decode/render latency of HTML5 Video/MediaSource to align lip-sync
    const AUDIO_PREBUFFER_SEC = 0.22;
    const PREBUFFER_TIMEOUT_MS = 280;
    let audioContext = null;
    let masterGain = null;
    let pcmWorkletNode = null;
    let workletInitPromise = null;
    let pendingWorkletChunks = [];
    let audioStack = [];
    let nextAudioTime = 0;
    let audioPrebuffer = [];
    let isPlayingAudio = false;
    let prebufferTimeout = null;
    let leftoverAudioBytes = null;

    const PCM_WORKLET_CODE = `
    class PcmPlayerProcessor extends AudioWorkletProcessor {
        constructor() {
            super();
            this.queue = [];
            this.readOffset = 0;
            this.bufferedSamples = 0;
            this.isPlaying = false;
            this.turnComplete = false;
            this.initialPrebufferSamples = Math.round(sampleRate * 0.22);
            this.rebufferSamples = Math.round(sampleRate * 0.08);
            this.currentThreshold = this.initialPrebufferSamples;
            this.fadeInTotal = Math.max(1, Math.round(sampleRate * 0.006));
            this.fadeInRemaining = 0;
            this.lastSample = 0;

            this.port.onmessage = (e) => {
                const msg = e.data;
                if (msg.type === 'samples' && msg.samples && msg.samples.length > 0) {
                    this.queue.push(msg.samples);
                    this.bufferedSamples += msg.samples.length;
                    this.turnComplete = false;
                    if (!this.isPlaying && this.bufferedSamples >= this.currentThreshold) {
                        this.isPlaying = true;
                        this.fadeInRemaining = this.fadeInTotal;
                    }
                } else if (msg.type === 'flush') {
                    this.turnComplete = Boolean(msg.turnComplete);
                    if (this.turnComplete && this.bufferedSamples === 0) {
                        this.currentThreshold = this.initialPrebufferSamples;
                    }
                    if (!this.isPlaying && this.bufferedSamples > 0) {
                        this.isPlaying = true;
                        this.fadeInRemaining = this.fadeInTotal;
                    }
                } else if (msg.type === 'clear') {
                    this.queue = [];
                    this.readOffset = 0;
                    this.bufferedSamples = 0;
                    this.isPlaying = false;
                    this.turnComplete = false;
                    this.currentThreshold = this.initialPrebufferSamples;
                    this.fadeInRemaining = 0;
                }
            };
        }

        process(inputs, outputs) {
            const output = outputs[0][0];
            if (!output) return true;

            for (let i = 0; i < output.length; i++) {
                if (this.isPlaying && this.bufferedSamples > 0) {
                    const chunk = this.queue[0];
                    let sample = chunk[this.readOffset++];
                    this.bufferedSamples--;
                    if (this.readOffset >= chunk.length) {
                        this.queue.shift();
                        this.readOffset = 0;
                    }

                    if (this.fadeInRemaining > 0) {
                        const progress = 1 - (this.fadeInRemaining / this.fadeInTotal);
                        const gain = 0.5 * (1 - Math.cos(Math.PI * progress));
                        sample = this.lastSample * (1 - gain) + sample * gain;
                        this.fadeInRemaining--;
                    }

                    output[i] = sample;
                    this.lastSample = sample;

                    if (this.bufferedSamples === 0) {
                        this.isPlaying = false;
                        this.currentThreshold = this.turnComplete
                            ? this.initialPrebufferSamples
                            : this.rebufferSamples;
                    }
                } else {
                    if (Math.abs(this.lastSample) > 1e-5) {
                        this.lastSample *= 0.92;
                        output[i] = this.lastSample;
                    } else {
                        this.lastSample = 0;
                        output[i] = 0;
                    }
                }
            }
            return true;
        }
    }
    registerProcessor('pcm-player-processor', PcmPlayerProcessor);
    `;
    
    let mediaSource = null;
    let sourceBuffer = null;
    let videoQueue = [];

    let micStream = null;
    let micAudioContext = null;
    let micProcessor = null;
    let isRecording = false;

    // Avatars and voices come from the backend (/config), which also holds the defaults
    let reconnectAfterClose = false;

    function addOption(select, value, label) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }

    // What the app opens on. The preset changes the wording and the suggestions, nothing else.
    const PRESETS = {
        learning: {
            role: 'Your tutor: Professor',
            welcome: 'Welcome. Click Connect, then ask by voice or by text. The tutor can draw, film, build scenes you can click and try, check your work on camera and discuss a research paper.',
            suggestions: [
                ['A water molecule in 3D', 'Show me a water molecule in 3D.'],
                ['Play with gradient descent', 'I want to play with gradient descent and change the learning rate.'],
                ['Explore the human body', 'Let me explore the human body: I want to click on the organs.'],
                ['A video of a volcano', 'Make a short video of a volcano erupting.'],
                ['Check my work on camera', 'Can you check what I am showing you and mark any mistake?'],
                ['Discuss a research paper', null],
            ],
        },
        research: {
            role: 'Your research guide:',
            welcome: 'Welcome. Click Connect, then load a paper: upload the PDF, paste an arXiv link or search for it. Ask about it by voice or by text, turn any figure or equation into something you can try, or practice presenting it.',
            suggestions: [
                ['Load a paper', null],
                ['Make a figure interactive', 'Make a figure of the paper interactive.'],
                ['Practice my poster pitch', 'I want to practice presenting my paper. Play a curious attendee and ask me questions.'],
                ['Question me like a reviewer', 'Question me about my paper as a demanding reviewer would.'],
                ['Draw a visual abstract', 'Draw a visual abstract of the paper.'],
                ['Play with gradient descent', 'I want to play with gradient descent and change the learning rate.'],
            ],
        },
    };
    let rolePrefix = PRESETS.learning.role;

    const modeSelect = document.getElementById('mode-select');
    const proactiveToggle = document.getElementById('proactive-toggle');
    let serverMode = { preset: 'learning', proactive: false };

    function remembered(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }

    function remember(key, value) {
        try { localStorage.setItem(key, value); } catch (e) { /* private browsing */ }
    }

    function showProactive() {
        document.getElementById('proactive-state').textContent = proactiveToggle.checked ? 'On' : 'Off';
    }

    // The mode chosen in the app overrides the one in .env, and is kept for the next visit
    function setupModes(config) {
        serverMode = { preset: PRESETS[config.preset] ? config.preset : 'learning', proactive: !!config.proactive };
        const preset = remembered('mode') || serverMode.preset;
        modeSelect.value = PRESETS[preset] ? preset : 'learning';
        const proactive = remembered('proactive');
        proactiveToggle.checked = proactive === null ? serverMode.proactive : proactive === 'on';
        showProactive();
        applyPreset({ ...config, preset: modeSelect.value });
    }

    function sendModes(changed) {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        const request = {};
        if (changed === 'preset' || (!changed && modeSelect.value !== serverMode.preset)) request.preset = modeSelect.value;
        if (changed === 'proactive' || (!changed && proactiveToggle.checked !== serverMode.proactive)) request.proactive = proactiveToggle.checked;
        if (Object.keys(request).length) socket.send(JSON.stringify({ modeRequest: request }));
    }

    modeSelect.addEventListener('change', () => {
        remember('mode', modeSelect.value);
        applyPreset({ preset: modeSelect.value });
        updateTutorName();
        sendModes('preset');
    });
    proactiveToggle.addEventListener('change', () => {
        remember('proactive', proactiveToggle.checked ? 'on' : 'off');
        showProactive();
        sendModes('proactive');
    });

    function applyPreset(config) {
        const preset = PRESETS[config.preset] || PRESETS.learning;
        rolePrefix = preset.role;
        if (config.appName) {
            document.title = config.appName;
            const heading = document.querySelector('.header-titles h1');
            if (heading) heading.textContent = config.appName;
        }
        const welcome = document.getElementById('welcome-text');
        if (welcome) welcome.textContent = preset.welcome;
        const holder = document.querySelector('.suggestions');
        if (!holder) return;
        holder.innerHTML = '';
        for (const [label, prompt] of preset.suggestions) {
            const chip = document.createElement('button');
            chip.className = 'suggestion';
            chip.textContent = label;
            chip.addEventListener('click', () => {
                if (!prompt) {
                    paperPopover.style.display = 'flex';
                    paperQuery.focus();
                    return;
                }
                userInput.value = prompt;
                sendMessage();
            });
            holder.appendChild(chip);
        }
    }

    async function populateTeacherPicker() {
        let config = { avatars: { 'Professional': ['Kira'] }, voices: { 'Aoede': 'Breezy' }, defaults: { avatar: 'Kira', voice: 'Aoede' } };
        try {
            const response = await fetch('/config');
            if (response.ok) config = await response.json();
        } catch (e) {
            console.warn('Could not load /config, using defaults:', e);
        }
        setupModes(config);
        avatarSelect.innerHTML = '';
        voiceSelect.innerHTML = '';
        for (const [style, names] of Object.entries(config.avatars)) {
            const group = document.createElement('optgroup');
            group.label = style;
            for (const name of names) {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                group.appendChild(option);
            }
            avatarSelect.appendChild(group);
        }
        for (const [name, description] of Object.entries(config.voices)) {
            addOption(voiceSelect, name, `${name} (${description.toLowerCase()})`);
        }
        let avatar = config.defaults.avatar;
        let voice = config.defaults.voice;
        try {
            avatar = localStorage.getItem('avatar') || avatar;
            voice = localStorage.getItem('voice') || voice;
        } catch (e) {}
        avatarSelect.value = avatar;
        voiceSelect.value = voice;
        if (!avatarSelect.value) avatarSelect.value = config.defaults.avatar;
        if (!voiceSelect.value) voiceSelect.value = config.defaults.voice;
        updateTutorName();
    }

    function updateTutorName() {
        tutorName.textContent = `Professor ${avatarSelect.value}`;
        const subtitle = document.querySelector('.header-titles p');
        if (subtitle) subtitle.textContent = `${rolePrefix} ${avatarSelect.value}`;
    }

    function onTeacherChange() {
        updateTutorName();
        try {
            localStorage.setItem('avatar', avatarSelect.value);
            localStorage.setItem('voice', voiceSelect.value);
        } catch (e) {}
        if (socket && socket.readyState === WebSocket.OPEN) {
            appendMessage("System", `Switching to Professor ${avatarSelect.value}...`, "system", false);
            reconnectAfterClose = true;
            disconnect();
        }
    }

    // Camera or screen input, sent to the model as JPEG frames at 1 fps
    let videoStream = null;
    let videoSource = null;
    let frameTimer = null;
    const frameCanvas = document.createElement('canvas');
    const FRAME_INTERVAL_MS = 1000;
    const FRAME_MAX_SIDE = 768;

    // Generated media cards, keyed by tool call id
    const mediaCards = new Map();

    function processVideoQueue() {
        if (!sourceBuffer || sourceBuffer.updating || videoQueue.length === 0 || mediaSource?.readyState !== 'open') {
            return;
        }
        try {
            sourceBuffer.appendBuffer(videoQueue.shift());
        } catch (e) {
            console.error("AppendBuffer failed:", e);
        }
    }

    function initMediaSource() {
        if (!window.MediaSource) {
            console.error("MediaSource is not supported in this browser.");
            return;
        }
        
        videoQueue = [];
        mediaSource = new MediaSource();
        avatarVideo.src = URL.createObjectURL(mediaSource);

        mediaSource.addEventListener('sourceopen', () => {
            console.log("MediaSource opened. Probing for codecs...");
            const codecs = [
                'video/mp4; codecs="avc1.42c020, mp4a.40.2"',
                'video/mp4; codecs="avc1.42E01E"',
                'video/mp4; codecs="avc1.4d001f"',
                'video/mp4; codecs="avc1.64001f"',
                'video/mp4; codecs="vp09.00.10.08"',
                'video/webm; codecs="vp9"',
                'video/mp4'
            ];

            let supportedCodec = null;
            for (const codec of codecs) {
                if (MediaSource.isTypeSupported(codec)) {
                    supportedCodec = codec;
                    break;
                }
            }

            if (supportedCodec) {
                console.log(`MediaSource using codec: ${supportedCodec}`);
                try {
                    sourceBuffer = mediaSource.addSourceBuffer(supportedCodec);
                    sourceBuffer.addEventListener('updateend', () => {
                        processVideoQueue();
                        skipVideoGap();
                        if (avatarVideo.paused && avatarVideo.readyState >= 3) {
                            avatarVideo.play().catch(e => {
                                avatarVideo.muted = true;
                                avatarVideo.play().catch(err => {});
                            });
                        }
                    });
                    processVideoQueue();
                } catch (err) {
                    console.error("Failed to add SourceBuffer:", err);
                }
            } else {
                console.error("No supported codecs found.");
            }
        });
    }

    function base64ToArrayBuffer(base64) {
        const cleanBase64 = base64.replace(/\s/g, '');
        const binaryString = window.atob(cleanBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }

    function initAudioContext() {
        if (!audioContext) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            try {
                audioContext = new AudioCtx({ sampleRate: AUDIO_SAMPLE_RATE, latencyHint: 'playback' });
            } catch (e) {
                audioContext = new AudioCtx({ latencyHint: 'playback' });
            }
            masterGain = audioContext.createGain();
            masterGain.gain.setValueAtTime(1, audioContext.currentTime);
            masterGain.connect(audioContext.destination);
            nextAudioTime = audioContext.currentTime;

            if (audioContext.audioWorklet && audioContext.sampleRate === AUDIO_SAMPLE_RATE) {
                const blob = new Blob([PCM_WORKLET_CODE], { type: 'application/javascript' });
                const workletUrl = URL.createObjectURL(blob);
                workletInitPromise = audioContext.audioWorklet.addModule(workletUrl).then(() => {
                    URL.revokeObjectURL(workletUrl);
                    pcmWorkletNode = new AudioWorkletNode(audioContext, 'pcm-player-processor');
                    pcmWorkletNode.connect(masterGain);
                    while (pendingWorkletChunks.length > 0) {
                        const chunk = pendingWorkletChunks.shift();
                        pcmWorkletNode.port.postMessage({ type: 'samples', samples: chunk }, [chunk.buffer]);
                    }
                }).catch((err) => {
                    URL.revokeObjectURL(workletUrl);
                    console.warn("AudioWorklet setup failed, falling back to AudioBufferSourceNode:", err);
                    workletInitPromise = null;
                    while (pendingWorkletChunks.length > 0) {
                        enqueueFallbackAudio(pendingWorkletChunks.shift());
                    }
                });
            }
        }
        if (audioContext.state === 'suspended') {
            audioContext.resume().catch(() => {});
        }
    }

    function pcm16ToFloat32(uint8Array) {
        let combined = uint8Array;
        if (leftoverAudioBytes && leftoverAudioBytes.length > 0) {
            const merged = new Uint8Array(leftoverAudioBytes.length + uint8Array.length);
            merged.set(leftoverAudioBytes, 0);
            merged.set(uint8Array, leftoverAudioBytes.length);
            combined = merged;
            leftoverAudioBytes = null;
        }

        const sampleCount = Math.floor(combined.length / 2);
        if (combined.length % 2 !== 0) {
            leftoverAudioBytes = combined.slice(sampleCount * 2);
        }

        const int16Array = new Int16Array(combined.buffer, combined.byteOffset, sampleCount);
        const float32Array = new Float32Array(sampleCount);
        for (let i = 0; i < sampleCount; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }
        return float32Array;
    }

    function mergeFloat32Chunks(chunks) {
        if (chunks.length === 1) return chunks[0];
        const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);
        const merged = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            merged.set(chunk, offset);
            offset += chunk.length;
        }
        return merged;
    }

    function scheduleAudioChunk(floatData, isFirstChunkOfTurn = false) {
        if (!audioContext || !masterGain || floatData.length === 0) return;

        const audioBuffer = audioContext.createBuffer(1, floatData.length, AUDIO_SAMPLE_RATE);
        audioBuffer.getChannelData(0).set(floatData);

        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;

        // Ensure start time is always safely ahead of the audio thread quantum to prevent chunk overlap
        const minStartTime = audioContext.currentTime + 0.02;
        if (nextAudioTime < minStartTime) {
            nextAudioTime = minStartTime;
        }

        // Apply a 6ms micro-fade on the first chunk of a turn to prevent DC offset clicks
        const chunkGain = audioContext.createGain();
        if (isFirstChunkOfTurn) {
            chunkGain.gain.setValueAtTime(0, nextAudioTime);
            chunkGain.gain.linearRampToValueAtTime(1, nextAudioTime + 0.006);
        } else {
            chunkGain.gain.setValueAtTime(1, nextAudioTime);
        }

        source.connect(chunkGain);
        chunkGain.connect(masterGain);

        source.start(nextAudioTime);
        nextAudioTime += audioBuffer.duration;

        audioStack.push(source);
        source.onended = () => {
            const idx = audioStack.indexOf(source);
            if (idx !== -1) audioStack.splice(idx, 1);
        };
    }

    function flushPrebuffer(turnComplete = false) {
        if (prebufferTimeout) {
            clearTimeout(prebufferTimeout);
            prebufferTimeout = null;
        }
        if (turnComplete) {
            leftoverAudioBytes = null;
        }
        if (pcmWorkletNode) {
            pcmWorkletNode.port.postMessage({ type: 'flush', turnComplete });
            if (turnComplete) isPlayingAudio = false;
            return;
        }
        if (workletInitPromise) {
            workletInitPromise.then(() => flushPrebuffer(turnComplete));
            return;
        }
        if (audioPrebuffer.length > 0) {
            const merged = mergeFloat32Chunks(audioPrebuffer);
            audioPrebuffer = [];
            const wasPlaying = isPlayingAudio;
            isPlayingAudio = true;
            if (!wasPlaying || nextAudioTime < audioContext.currentTime + 0.02) {
                nextAudioTime = audioContext.currentTime + 0.05;
            }
            scheduleAudioChunk(merged, !wasPlaying);
        }
        if (turnComplete) {
            isPlayingAudio = false;
        }
    }

    function enqueueFallbackAudio(floatData) {
        if (isPlayingAudio) {
            if (nextAudioTime < audioContext.currentTime + 0.02) {
                nextAudioTime = audioContext.currentTime + 0.05;
                scheduleAudioChunk(floatData, true);
            } else {
                scheduleAudioChunk(floatData, false);
            }
            return;
        }

        audioPrebuffer.push(floatData);
        const bufferedSamples = audioPrebuffer.reduce((sum, c) => sum + c.length, 0);
        const bufferedSec = bufferedSamples / AUDIO_SAMPLE_RATE;

        if (bufferedSec >= AUDIO_PREBUFFER_SEC) {
            flushPrebuffer(false);
        }
    }

    function queueAudioFrame(mimeType, base64Data) {
        initAudioContext();
        if (!audioContext) return;

        const arrayBuffer = base64ToArrayBuffer(base64Data);
        const floatData = pcm16ToFloat32(new Uint8Array(arrayBuffer));
        if (floatData.length === 0) return;

        // Reset sliding fallback timeout so short turns or trailing chunks still flush
        if (prebufferTimeout) clearTimeout(prebufferTimeout);
        prebufferTimeout = setTimeout(() => {
            flushPrebuffer(false);
        }, PREBUFFER_TIMEOUT_MS);

        if (pcmWorkletNode) {
            isPlayingAudio = true;
            pcmWorkletNode.port.postMessage({ type: 'samples', samples: floatData }, [floatData.buffer]);
            return;
        }
        if (workletInitPromise) {
            isPlayingAudio = true;
            pendingWorkletChunks.push(floatData);
            return;
        }

        enqueueFallbackAudio(floatData);
    }

    function stopAudio() {
        if (prebufferTimeout) {
            clearTimeout(prebufferTimeout);
            prebufferTimeout = null;
        }
        audioPrebuffer = [];
        pendingWorkletChunks = [];
        isPlayingAudio = false;
        leftoverAudioBytes = null;

        if (masterGain && audioContext) {
            try {
                // Smooth 10ms fade out to avoid abrupt cutoff clicks on interruption
                masterGain.gain.cancelScheduledValues(audioContext.currentTime);
                masterGain.gain.setValueAtTime(masterGain.gain.value, audioContext.currentTime);
                masterGain.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.01);
            } catch (e) {}
        }

        setTimeout(() => {
            if (pcmWorkletNode) {
                pcmWorkletNode.port.postMessage({ type: 'clear' });
            }
            audioStack.forEach(source => {
                try { source.stop(); } catch (e) {}
            });
            audioStack = [];
            if (masterGain && audioContext) {
                masterGain.gain.cancelScheduledValues(audioContext.currentTime);
                masterGain.gain.setValueAtTime(1, audioContext.currentTime);
            }
            if (audioContext) {
                nextAudioTime = audioContext.currentTime;
            }
        }, 12);
    }

    // Drop the avatar video that is buffered but not yet played, so an interruption cuts it short
    function flushAvatarVideo() {
        videoQueue = [];
        if (!sourceBuffer || mediaSource?.readyState !== 'open') return;
        try {
            if (sourceBuffer.updating) sourceBuffer.abort();
            const buffered = sourceBuffer.buffered;
            if (buffered.length) {
                const from = avatarVideo.currentTime + 0.1;
                const end = buffered.end(buffered.length - 1);
                if (end > from) sourceBuffer.remove(from, end);
            }
        } catch (e) {
            console.warn("Could not flush avatar video:", e);
        }
    }

    // After a flush the next response starts later on the timeline; jump over the gap
    function skipVideoGap() {
        const buffered = avatarVideo.buffered;
        if (!buffered.length) return;
        const lastStart = buffered.start(buffered.length - 1);
        if (avatarVideo.currentTime < lastStart - 0.05) {
            avatarVideo.currentTime = lastStart;
        }
    }

    let lastSpeaker = null;
    let lastMessageEl = null;

    function appendMessage(author, text, type, isStreaming = true) {
        if (isStreaming && lastSpeaker === type && lastMessageEl) {
            lastMessageEl.textContent += " " + text;
            lastMessageEl.textContent = lastMessageEl.textContent.replace(/\s+/g, ' ');
            chatLog.scrollTop = chatLog.scrollHeight;
        } else {
            const messageEl = document.createElement('div');
            messageEl.className = `message ${type}`;
            messageEl.textContent = text;
            chatLog.appendChild(messageEl);
            chatLog.scrollTop = chatLog.scrollHeight;
            lastSpeaker = type;
            lastMessageEl = messageEl;
        }
    }

    const KINDS = {
        image: { noun: 'image', label: 'Image', model: 'Nano Banana', icon: 'image' },
        video: { noun: 'video', label: 'Video', model: 'Gemini Omni', icon: 'movie' },
        scene: { noun: 'interactive scene', label: 'Scene', model: 'Gemini', icon: 'view_in_ar' },
    };

    function mediaKind(kind) {
        return KINDS[kind] ? kind : 'image';
    }

    function mediaLabel(kind, state) {
        const { noun, model } = KINDS[mediaKind(kind)];
        const title = noun.charAt(0).toUpperCase() + noun.slice(1);
        if (state === 'pending') return `Generating ${noun} with ${model}`;
        if (state === 'failed') return `${title} generation failed`;
        return `${title} generated with ${model}`;
    }

    // Artifacts Pane State & Management: 'expanded' | 'minimized'
    const artifactsMap = new Map(); // id -> artifact
    let activeArtifactId = null;
    let artifactsPaneMode = 'expanded'; // 'expanded' | 'minimized'

    function formatArtifactTime(date) {
        if (!date) return '';
        const d = date instanceof Date ? date : new Date(date);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function registerArtifact(id, kind, prompt) {
        let artifact = artifactsMap.get(id);
        if (!artifact) {
            artifact = {
                id,
                kind,
                prompt: prompt || '',
                state: 'pending',
                timestamp: new Date(),
                model: KINDS[mediaKind(kind)].model,
                url: null,
                mimeType: null,
                data: null,
                error: null
            };
            artifactsMap.set(id, artifact);
        } else {
            artifact.kind = kind;
            if (prompt) artifact.prompt = prompt;
        }
        activeArtifactId = id;
        if (artifactsPaneMode === 'expanded') {
            expandArtifactsPane();
        } else {
            minimizeArtifactsPane();
        }
        return artifact;
    }

    function completeArtifact(media) {
        const kind = mediaKind(media.kind);
        const mimeType = media.mimeType || media.mime_type || (kind === 'video' ? 'video/mp4' : 'image/png');
        const blob = new Blob([base64ToArrayBuffer(media.data)], { type: mimeType });
        const url = URL.createObjectURL(blob);

        let artifact = artifactsMap.get(media.id);
        if (!artifact) {
            artifact = {
                id: media.id,
                kind,
                prompt: media.prompt || '',
                timestamp: new Date(),
                model: KINDS[mediaKind(kind)].model
            };
            artifactsMap.set(media.id, artifact);
        }
        artifact.state = 'done';
        artifact.url = url;
        artifact.mimeType = mimeType;
        artifact.data = media.data;
        if (media.prompt) artifact.prompt = media.prompt;
        if (media.tool === 'show_paper_part') artifact.model = 'From the paper';
        if (media.tool === 'generate_illustrated_scene') artifact.model = 'Nano Banana + Gemini';
        if (media.sourceImage) {
            if (artifact.source) URL.revokeObjectURL(artifact.source.url);
            artifact.source = {
                url: URL.createObjectURL(new Blob([base64ToArrayBuffer(media.sourceImage)], { type: 'image/jpeg' })),
                label: `${media.sourceLabel || 'The paper'}, page ${media.sourcePage}`,
            };
        }
        if (kind === 'scene') {
            artifact.html = new TextDecoder().decode(base64ToArrayBuffer(media.data));
            artifact.frame = null;
            artifact.errorReported = false;
        }

        if (!activeArtifactId || activeArtifactId === media.id || kind === 'scene') {
            activeArtifactId = media.id;
        }

        // a scene only runs in the pane, so it always opens there
        if (artifactsPaneMode === 'expanded' || kind === 'scene') {
            expandArtifactsPane();
        } else {
            minimizeArtifactsPane();
        }
        return { artifact, url, mimeType };
    }

    function failArtifact(error) {
        const kind = mediaKind(error.kind);
        let artifact = artifactsMap.get(error.id);
        if (!artifact) {
            artifact = {
                id: error.id,
                kind,
                prompt: '',
                timestamp: new Date(),
                model: KINDS[mediaKind(kind)].model
            };
            artifactsMap.set(error.id, artifact);
        }
        artifact.state = 'failed';
        artifact.error = error.message || 'Generation failed.';
        renderArtifactsPane();
        return artifact;
    }

    function expandArtifactsPane() {
        if (!artifactsPane) return;
        artifactsPaneMode = 'expanded';
        artifactsPane.style.display = 'flex';
        artifactsPane.classList.remove('minimized');
        if (appContainer) {
            appContainer.classList.add('has-artifacts-pane');
            appContainer.classList.remove('artifacts-minimized');
        }
        if (artifactsToggleBtn) {
            artifactsToggleBtn.classList.add('active');
            artifactsToggleBtn.title = 'Minimize Artifacts Pane';
        }
        if (artifactsExpandBtn) artifactsExpandBtn.style.display = 'none';
        if (artifactsCloseBtn) artifactsCloseBtn.style.display = 'flex';
        renderArtifactsPane();
    }

    function minimizeArtifactsPane() {
        if (!artifactsPane) return;
        if (artifactsMap.size === 0) {
            hideArtifactsPane();
            return;
        }
        artifactsPaneMode = 'minimized';
        artifactsPane.style.display = 'flex';
        artifactsPane.classList.add('minimized');
        if (appContainer) {
            appContainer.classList.add('has-artifacts-pane', 'artifacts-minimized');
        }
        if (artifactsToggleBtn) {
            artifactsToggleBtn.classList.remove('active');
            artifactsToggleBtn.title = 'Expand Artifacts Pane';
        }
        if (artifactsExpandBtn) artifactsExpandBtn.style.display = 'flex';
        if (artifactsCloseBtn) artifactsCloseBtn.style.display = 'none';
        renderArtifactsPane();
    }

    function hideArtifactsPane() {
        if (!artifactsPane) return;
        // the stage is always there; with nothing to show it presents the suggestions
        artifactsPaneMode = 'expanded';
        if (artifactsEmpty) artifactsEmpty.style.display = '';
        if (artifactsContent) artifactsContent.style.display = 'none';
        if (appContainer) appContainer.classList.remove('has-artifacts-pane', 'artifacts-minimized');
        if (artifactsToggleBtn) artifactsToggleBtn.classList.remove('active');
    }

    function toggleArtifactsPane() {
        if (artifactsPaneMode === 'expanded') {
            minimizeArtifactsPane();
        } else {
            expandArtifactsPane();
        }
    }

    function selectArtifact(id) {
        if (!artifactsMap.has(id)) return;
        activeArtifactId = id;
        expandArtifactsPane();
        renderArtifactsPane();
    }

    function renderArtifactsPane() {
        const count = artifactsMap.size;
        if (artifactsBadgeCount) artifactsBadgeCount.textContent = count;
        if (artifactsPaneCount) {
            artifactsPaneCount.textContent = artifactsPaneMode === 'minimized' ? `${count}` : `${count} ${count === 1 ? 'item' : 'items'}`;
        }
        
        if (count > 0 && artifactsToggleBtn) {
            artifactsToggleBtn.style.display = 'inline-flex';
        }

        if (count === 0) {
            hideArtifactsPane();
            return;
        }

        if (artifactsEmpty) artifactsEmpty.style.display = 'none';
        if (artifactsContent) artifactsContent.style.display = 'flex';

        // Featured stage (only populated when expanded)
        const active = artifactsMap.get(activeArtifactId) || Array.from(artifactsMap.values())[artifactsMap.size - 1];
        if (!active) return;
        activeArtifactId = active.id;

        if (artifactsPaneMode === 'expanded' && featuredMediaWrapper) {
            // a running scene stays in place across renders; re-inserting an iframe reloads it
            const liveScene = active.kind === 'scene' && active.state === 'done';
            const keepFrame = liveScene && active.frame && active.frame.parentElement === featuredMediaWrapper;
            if (!keepFrame) featuredMediaWrapper.innerHTML = '';
            featuredMediaWrapper.classList.toggle('scene', liveScene);
            featuredMediaWrapper.classList.toggle('beside', liveScene && sourceVisible(active));
            updateSourceButton(active, liveScene);
            if (!liveScene) featuredMediaWrapper.parentElement.classList.remove('scene-expanded');
            if (active.state === 'pending') {
                const pendingBox = document.createElement('div');
                pendingBox.className = 'featured-pending';
                pendingBox.innerHTML = `
                    <div class="spinner"></div>
                    <div class="featured-pending-text">Generating ${active.kind} with ${active.model}...</div>
                    <div class="featured-pending-prompt">${active.prompt ? `"${active.prompt}"` : ''}</div>
                `;
                featuredMediaWrapper.appendChild(pendingBox);

                if (featuredTypePill) {
                    featuredTypePill.innerHTML = `<span class="material-icons" style="font-size: 14px;">hourglass_top</span> Pending`;
                }
                if (featuredModelPill) featuredModelPill.textContent = active.model;
                if (featuredTime) featuredTime.textContent = formatArtifactTime(active.timestamp);
                if (featuredPrompt) {
                    featuredPrompt.textContent = active.prompt;
                    featuredPrompt.style.display = active.prompt ? 'block' : 'none';
                }

                if (featuredDownloadBtn) featuredDownloadBtn.style.display = 'none';
                if (featuredFullscreenBtn) featuredFullscreenBtn.style.display = 'none';
                if (featuredCopyBtn) featuredCopyBtn.style.display = active.prompt ? 'inline-flex' : 'none';
            } else if (active.state === 'failed') {
                const failedBox = document.createElement('div');
                failedBox.className = 'featured-failed';
                failedBox.innerHTML = `
                    <span class="material-icons">error_outline</span>
                    <div style="font-weight: 600;">Generation Failed</div>
                    <div class="featured-failed-msg">${active.error || 'An error occurred during generation.'}</div>
                `;
                featuredMediaWrapper.appendChild(failedBox);

                if (featuredTypePill) {
                    featuredTypePill.innerHTML = `<span class="material-icons" style="font-size: 14px;">warning</span> Failed`;
                }
                if (featuredModelPill) featuredModelPill.textContent = active.model;
                if (featuredTime) featuredTime.textContent = formatArtifactTime(active.timestamp);
                if (featuredPrompt) {
                    featuredPrompt.textContent = active.prompt;
                    featuredPrompt.style.display = active.prompt ? 'block' : 'none';
                }

                if (featuredDownloadBtn) featuredDownloadBtn.style.display = 'none';
                if (featuredFullscreenBtn) featuredFullscreenBtn.style.display = 'none';
                if (featuredCopyBtn) featuredCopyBtn.style.display = active.prompt ? 'inline-flex' : 'none';
            } else {
                // Done
                let mediaEl;
                if (active.kind === 'scene') {
                    mediaEl = keepFrame ? null : createSceneFrame(active);
                } else if (active.kind === 'video') {
                    mediaEl = document.createElement('video');
                    mediaEl.src = active.url;
                    mediaEl.controls = true;
                    mediaEl.autoplay = true;
                    mediaEl.loop = true;
                    mediaEl.muted = true;
                    mediaEl.title = 'Drag left or right to scrub through the video';
                    attachScrub(mediaEl);
                    mediaEl.playsInline = true;
                } else {
                    mediaEl = document.createElement('img');
                    mediaEl.src = active.url;
                    mediaEl.alt = active.prompt || 'Generated image';
                    mediaEl.title = 'Click to view full size';
                    mediaEl.addEventListener('click', () => openLightbox(active));
                }
                if (mediaEl) featuredMediaWrapper.appendChild(mediaEl);
                syncSourcePage(active, liveScene);

                if (featuredTypePill) {
                    featuredTypePill.innerHTML = `<span class="material-icons" style="font-size: 14px;">${KINDS[mediaKind(active.kind)].icon}</span> ${KINDS[mediaKind(active.kind)].label}`;
                }
                if (featuredModelPill) featuredModelPill.textContent = active.model;
                if (featuredTime) featuredTime.textContent = formatArtifactTime(active.timestamp);
                if (featuredPrompt) {
                    featuredPrompt.textContent = active.prompt;
                    featuredPrompt.style.display = active.prompt ? 'block' : 'none';
                }

                if (featuredDownloadBtn) {
                    featuredDownloadBtn.style.display = 'inline-flex';
                    featuredDownloadBtn.href = active.url;
                    const ext = (active.mimeType && active.mimeType.split('/')[1]) || (active.kind === 'video' ? 'mp4' : 'png');
                    featuredDownloadBtn.download = `${active.kind}-${active.id}.${ext}`;
                }

                if (featuredFullscreenBtn) {
                    featuredFullscreenBtn.style.display = 'inline-flex';
                    featuredFullscreenBtn.onclick = () => {
                        if (active.kind === 'scene') featuredMediaWrapper.parentElement.classList.toggle('scene-expanded');
                        else openLightbox(active);
                    };
                }

                if (featuredCopyBtn) featuredCopyBtn.style.display = active.prompt ? 'inline-flex' : 'none';
            }
        }

        // Render gallery strip
        if (artifactsGalleryStrip) {
            artifactsGalleryStrip.innerHTML = '';
            const list = Array.from(artifactsMap.values()).reverse(); // newest first
            for (const item of list) {
                const thumb = document.createElement('div');
                thumb.className = `artifact-thumb ${item.id === activeArtifactId ? 'active' : ''} ${item.state === 'pending' ? 'pending-thumb' : ''} ${item.state === 'failed' ? 'failed-thumb' : ''}`;
                thumb.title = item.prompt || `${item.kind} artifact`;

                if (item.state === 'pending') {
                    const sp = document.createElement('div');
                    sp.className = 'spinner small';
                    thumb.appendChild(sp);
                } else if (item.state === 'failed') {
                    const icon = document.createElement('span');
                    icon.className = 'material-icons';
                    icon.textContent = 'broken_image';
                    thumb.appendChild(icon);
                } else if (item.kind === 'scene') {
                    const icon = document.createElement('span');
                    icon.className = 'material-icons scene-thumb-icon';
                    icon.textContent = 'view_in_ar';
                    thumb.appendChild(icon);
                } else if (item.kind === 'video') {
                    const videoThumb = document.createElement('video');
                    videoThumb.src = item.url;
                    videoThumb.muted = true;
                    videoThumb.preload = 'metadata';
                    thumb.appendChild(videoThumb);
                } else {
                    const imgThumb = document.createElement('img');
                    imgThumb.src = item.url;
                    imgThumb.alt = item.prompt || 'Thumbnail';
                    thumb.appendChild(imgThumb);
                }

                const badge = document.createElement('div');
                badge.className = 'artifact-thumb-badge';
                const badgeIcon = document.createElement('span');
                badgeIcon.className = 'material-icons';
                badgeIcon.textContent = KINDS[mediaKind(item.kind)].icon;
                badge.appendChild(badgeIcon);
                thumb.appendChild(badge);

                thumb.addEventListener('click', () => selectArtifact(item.id));
                artifactsGalleryStrip.appendChild(thumb);
            }
        }
    }

    function openLightbox(artifact) {
        if (!artifact || artifact.state !== 'done' || artifact.kind === 'scene' || !mediaLightbox) return;
        if (lightboxContent) lightboxContent.innerHTML = '';
        let mediaEl;
        if (artifact.kind === 'video') {
            mediaEl = document.createElement('video');
            mediaEl.src = artifact.url;
            mediaEl.controls = true;
            mediaEl.autoplay = true;
            mediaEl.loop = true;
            mediaEl.playsInline = true;
        } else {
            mediaEl = document.createElement('img');
            mediaEl.src = artifact.url;
            mediaEl.alt = artifact.prompt || 'Full size artifact';
        }
        if (lightboxContent) lightboxContent.appendChild(mediaEl);
        if (lightboxCaption) {
            lightboxCaption.textContent = artifact.prompt ? `"${artifact.prompt}"` : `${artifact.kind} (${artifact.model})`;
        }
        mediaLightbox.style.display = 'flex';
    }

    function closeLightbox() {
        if (!mediaLightbox) return;
        const vid = lightboxContent ? lightboxContent.querySelector('video') : null;
        if (vid) vid.pause();
        mediaLightbox.style.display = 'none';
        if (lightboxContent) lightboxContent.innerHTML = '';
    }

    function createMediaCard(id, kind, prompt) {
        // Register artifact in the separate pane store
        registerArtifact(id, kind, prompt);

        const card = document.createElement('div');
        card.className = `message media-card pending ${kind}`;
        card.dataset.id = id;

        const header = document.createElement('div');
        header.className = 'media-header';
        const icon = document.createElement('span');
        icon.className = 'material-icons';
        icon.textContent = KINDS[mediaKind(kind)].icon;
        const label = document.createElement('span');
        label.className = 'media-label';
        label.textContent = mediaLabel(kind, 'pending');
        header.append(icon, label);

        const promptEl = document.createElement('p');
        promptEl.className = 'media-prompt';
        promptEl.textContent = prompt;

        const body = document.createElement('div');
        body.className = 'media-body';
        const spinner = document.createElement('div');
        spinner.className = 'spinner small';
        body.appendChild(spinner);

        card.append(header, promptEl, body);

        // Clicking the media card focuses it in the artifacts pane
        card.addEventListener('click', (e) => {
            if (e.target.closest('a') || e.target.closest('button')) return;
            selectArtifact(id);
        });

        chatLog.appendChild(card);
        chatLog.scrollTop = chatLog.scrollHeight;

        // The next transcript chunk starts a new bubble below the card
        lastSpeaker = null;
        lastMessageEl = null;

        mediaCards.set(id, card);
        return card;
    }

    function showGeneratedMedia(media) {
        finishActivity(media.id, 'done', media.durationMs);
        const { artifact, url, mimeType } = completeArtifact(media);
        const kind = artifact.kind;
        const card = mediaCards.get(media.id) || createMediaCard(media.id, kind, media.prompt || '');

        const body = card.querySelector('.media-body');
        body.innerHTML = '';
        let element;
        if (kind === 'scene') {
            element = document.createElement('button');
            element.type = 'button';
            element.className = 'scene-open-btn';
            element.innerHTML = '<span class="material-icons">view_in_ar</span> Open the interactive scene';
            element.onclick = (e) => {
                e.stopPropagation();
                selectArtifact(media.id);
            };
        } else if (kind === 'video') {
            element = document.createElement('video');
            element.src = url;
            element.controls = true;
            element.autoplay = true;
            element.loop = true;
            element.muted = true;
            element.playsInline = true;
        } else {
            element = document.createElement('img');
            element.src = url;
            element.alt = media.prompt || 'Generated image';
            element.addEventListener('click', (e) => {
                e.stopPropagation();
                selectArtifact(media.id);
            });
        }
        body.appendChild(element);

        // a repaired scene arrives under the same id and replaces the first result
        card.querySelector('.media-footer')?.remove();
        const footer = document.createElement('div');
        footer.className = 'media-footer';

        const viewInPaneBtn = document.createElement('button');
        viewInPaneBtn.type = 'button';
        viewInPaneBtn.className = 'view-in-pane-btn';
        viewInPaneBtn.innerHTML = '<span class="material-icons">visibility</span> View in Pane';
        viewInPaneBtn.onclick = (e) => {
            e.stopPropagation();
            selectArtifact(media.id);
        };
        footer.appendChild(viewInPaneBtn);

        const link = document.createElement('a');
        link.href = url;
        link.download = `${kind}-${media.id}.${mimeType.split('/')[1] || 'bin'}`;
        const linkIcon = document.createElement('span');
        linkIcon.className = 'material-icons';
        linkIcon.textContent = 'download';
        link.append(linkIcon, document.createTextNode('Download'));
        footer.appendChild(link);
        card.appendChild(footer);

        card.classList.remove('pending');
        card.querySelector('.media-label').textContent = media.tool === 'show_paper_part' ? 'From the paper'
            : media.tool === 'generate_illustrated_scene' ? 'Illustrated scene: image with clickable parts' : mediaLabel(kind, 'done');
        if (media.tool === 'show_paper_part') artifact.model = 'From the paper';
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function showGenerationError(error) {
        finishActivity(error.id, 'failed');
        failArtifact(error);
        const kind = mediaKind(error.kind);
        const card = mediaCards.get(error.id) || createMediaCard(error.id, kind, '');
        const body = card.querySelector('.media-body');
        body.innerHTML = '';
        body.textContent = error.message || 'Generation failed.';
        card.classList.remove('pending');
        card.classList.add('failed');
        card.querySelector('.media-label').textContent = mediaLabel(kind, 'failed');
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    // the page of the paper a scene was built from, shown next to it
    function sourceVisible(artifact) {
        return artifact.kind === 'scene' && artifact.state === 'done' && !!artifact.source && !!artifact.showSource;
    }

    function updateSourceButton(active, liveScene) {
        if (!featuredSourceBtn) return;
        featuredSourceBtn.style.display = liveScene && active.source ? 'inline-flex' : 'none';
        featuredSourceBtn.querySelector('span:last-child').textContent = sourceVisible(active) ? 'Hide paper' : 'Show in paper';
        featuredSourceBtn.onclick = () => {
            active.showSource = !active.showSource;
            if (active.showSource) {
                featuredMediaWrapper.parentElement.classList.add('scene-expanded');
            }
            renderArtifactsPane();
        };
    }

    function syncSourcePage(active, liveScene) {
        const existing = featuredMediaWrapper.querySelector('.scene-side-box');
        if (existing) existing.remove();
        if (!liveScene || !sourceVisible(active)) return;
        const box = document.createElement('div');
        box.className = 'scene-side-box';
        const tag = document.createElement('span');
        tag.textContent = active.source.label;
        const image = document.createElement('img');
        image.src = active.source.url;
        image.alt = `${active.source.label} of the paper`;
        image.title = 'Open the page at full size';
        image.addEventListener('click', () => window.open(active.source.url, '_blank', 'noopener'));
        box.append(tag, image);
        featuredMediaWrapper.appendChild(box);
    }

    function createSceneFrame(artifact) {
        const frame = document.createElement('iframe');
        frame.className = 'scene-frame';
        frame.title = artifact.prompt || 'Interactive scene';
        // scripts only: the generated page cannot read this page, its storage or its cookies
        frame.setAttribute('sandbox', 'allow-scripts');
        frame.srcdoc = artifact.html;
        artifact.frame = frame;
        return frame;
    }

    function sendSceneEvent(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ sceneEvent: payload }));
        }
    }

    function describeDetail(detail) {
        if (detail === null || detail === undefined) return '';
        if (typeof detail === 'object') return Object.values(detail).join(', ');
        return String(detail);
    }

    // Messages from a scene: what the learner did in it, or a script error
    window.addEventListener('message', (e) => {
        const data = e.data;
        if (!data || data.scene !== true) return;
        const artifact = Array.from(artifactsMap.values()).find(a => a.frame && a.frame.contentWindow === e.source);
        if (!artifact) return;
        if (data.type === 'error') {
            if (artifact.errorReported) return;
            artifact.errorReported = true;
            console.warn(`Scene ${artifact.id} failed:`, data.message);
            addActivityRow('build', 'Scene script error', String(data.message || ''));
            sendSceneEvent({ id: artifact.id, type: 'error', message: String(data.message || '') });
            return;
        }
        let detail = data.detail === undefined ? null : data.detail;
        try {
            JSON.stringify(detail);
        } catch (err) {
            detail = null;
        }
        addActivityRow('touch_app', `Learner: ${data.name}`, describeDetail(detail));
        sendSceneEvent({ id: artifact.id, type: 'event', name: String(data.name || ''), detail });
    });

    // Tutor activity: which tool and model ran, and how long it took
    const TOOL_LABELS = {
        generate_image: 'Image',
        edit_image: 'Image edit',
        annotate_current_view: 'Markup on your view',
        load_paper: 'Reading the paper',
        ask_paper: 'Question to the paper',
        prepare_questions: 'Preparing questions on the paper',
        show_paper_part: 'From the paper',
        generate_video: 'Video',
        edit_video: 'Video edit',
        generate_interactive_scene: 'Interactive scene (code)',
        generate_illustrated_scene: 'Illustrated scene (image with clickable parts)',
        edit_interactive_scene: 'Scene edit (code)',
    };
    const ACTIVITY_MAX_ROWS = 30;
    const activities = new Map(); // generation id -> { row, time, startedAt }
    let activityTimer = null;

    function addActivityRow(icon, title, subtitle) {
        const row = document.createElement('div');
        row.className = 'activity-row';
        const iconEl = document.createElement('span');
        iconEl.className = 'material-icons';
        iconEl.textContent = icon;
        const text = document.createElement('div');
        text.className = 'activity-text';
        const name = document.createElement('div');
        name.className = 'activity-name';
        name.textContent = title;
        const sub = document.createElement('div');
        sub.className = 'activity-sub';
        sub.textContent = subtitle || '';
        text.append(name, sub);
        const time = document.createElement('span');
        time.className = 'activity-time';
        row.append(iconEl, text, time);
        activityList.prepend(row);
        while (activityList.children.length > ACTIVITY_MAX_ROWS) activityList.lastElementChild.remove();
        activityPanel.style.display = 'block';
        return { row, time };
    }

    function startActivity(started) {
        const { row, time } = addActivityRow(started.kind === 'paper' ? 'description' : KINDS[mediaKind(started.kind)].icon,
            TOOL_LABELS[started.tool] || started.tool, started.model || '');
        row.classList.add('pending');
        activities.set(started.id, { row, time, startedAt: performance.now() });
        if (activityTimer) return;
        activityTimer = setInterval(() => {
            if (activities.size === 0) {
                clearInterval(activityTimer);
                activityTimer = null;
                return;
            }
            const now = performance.now();
            for (const activity of activities.values()) {
                activity.time.textContent = `${((now - activity.startedAt) / 1000).toFixed(1)} s`;
            }
        }, 100);
    }

    function finishActivity(id, state, durationMs) {
        const activity = activities.get(id);
        if (!activity) return;
        activities.delete(id);
        activity.row.classList.remove('pending');
        activity.row.classList.add(state);
        const ms = durationMs ?? (performance.now() - activity.startedAt);
        activity.time.textContent = state === 'failed' ? 'failed' : `${(ms / 1000).toFixed(1)} s`;
    }

    // Clears the conversation, the artifacts and the activity, and starts a new session with the avatar
    function resetSession() {
        for (const artifact of artifactsMap.values()) {
            if (artifact.url) URL.revokeObjectURL(artifact.url);
            if (artifact.source) URL.revokeObjectURL(artifact.source.url);
        }
        artifactsMap.clear();
        mediaCards.clear();
        activities.clear();
        activeArtifactId = null;
        featuredMediaWrapper.innerHTML = '';
        featuredMediaWrapper.parentElement.classList.remove('scene-expanded');
        artifactsGalleryStrip.innerHTML = '';
        hideArtifactsPane();
        artifactsPaneMode = 'expanded';
        artifactsToggleBtn.style.display = 'none';
        artifactsBadgeCount.textContent = '0';
        activityList.innerHTML = '';
        activityPanel.style.display = 'none';
        paperBadge.style.display = 'none';
        paperPopover.style.display = 'none';
        uploads.splice(0).forEach((upload) => URL.revokeObjectURL(upload.url));
        renderUploads();
        while (chatLog.children.length > 1) chatLog.lastElementChild.remove();
        lastSpeaker = null;
        lastMessageEl = null;
        if (socket && socket.readyState === WebSocket.OPEN) {
            reconnectAfterClose = true;
            disconnect();
        }
    }

    // Uploaded pictures: kept by the backend as references, in upload order
    const UPLOAD_MAX = 8;
    const UPLOAD_MAX_SIDE = 2048;
    const uploadTray = document.getElementById('upload-tray');
    const uploads = []; // { name, url }

    function renderUploads() {
        uploadTray.innerHTML = '';
        uploads.forEach((upload, index) => {
            const chip = document.createElement('div');
            chip.className = 'upload-chip';
            chip.title = upload.name;
            const image = document.createElement('img');
            image.src = upload.url;
            image.alt = upload.name;
            const label = document.createElement('span');
            label.textContent = `Image ${index + 1}`;
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.title = `Remove ${upload.name}`;
            remove.innerHTML = '<span class="material-icons">close</span>';
            remove.onclick = () => {
                uploads.splice(index, 1);
                URL.revokeObjectURL(upload.url);
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ uploadRemove: { index } }));
                }
                renderUploads();
            };
            chip.append(image, label, remove);
            uploadTray.appendChild(chip);
        });
    }

    async function addUpload(file) {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            appendMessage("System", "Not connected to backend.", 'system');
            return;
        }
        if (uploads.length >= UPLOAD_MAX) {
            appendMessage("System", `You can keep up to ${UPLOAD_MAX} pictures. Remove one to add another.`, 'system');
            return;
        }
        let bitmap;
        try {
            bitmap = await createImageBitmap(file);
        } catch (err) {
            appendMessage("System", `${file.name} could not be read as a picture.`, 'system');
            return;
        }
        // phone photos are large; references do not need more than this
        const scale = Math.min(1, UPLOAD_MAX_SIDE / Math.max(bitmap.width, bitmap.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(bitmap.width * scale);
        canvas.height = Math.round(bitmap.height * scale);
        canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
        const blob = await (await fetch(dataUrl)).blob();
        uploads.push({ name: file.name, url: URL.createObjectURL(blob) });
        socket.send(JSON.stringify({ uploadRequest: { name: file.name, mimeType: 'image/jpeg', data: dataUrl.split(',')[1] } }));
        renderUploads();
    }

    // Dragging across a video scrubs through it, so a clip of something turning can be turned by hand
    function attachScrub(video) {
        let start = null;
        let scrubbed = false;
        video.addEventListener('pointerdown', (e) => {
            const box = video.getBoundingClientRect();
            // leave the player's own controls alone
            if (e.clientY > box.bottom - 48) return;
            start = { x: e.clientX, time: video.currentTime, width: box.width };
            scrubbed = false;
        });
        video.addEventListener('pointermove', (e) => {
            if (!start || !video.duration) return;
            const moved = e.clientX - start.x;
            if (!scrubbed && Math.abs(moved) < 5) return;
            if (!scrubbed) {
                scrubbed = true;
                video.pause();
                video.setPointerCapture(e.pointerId);
            }
            const time = (start.time + (moved / start.width) * video.duration) % video.duration;
            video.currentTime = time < 0 ? time + video.duration : time;
        });
        video.addEventListener('pointerup', () => {
            start = null;
        });
        video.addEventListener('click', (e) => {
            // the click that ends a drag must not restart playback
            if (scrubbed) e.preventDefault();
            scrubbed = false;
        });
    }

    // Research papers: an uploaded PDF or a link, read by the backend
    const PAPER_LINK = /^(https:\/\/(www\.|export\.)?(arxiv\.org|openreview\.net|proceedings\.neurips\.cc|papers\.nips\.cc|proceedings\.mlr\.press|aclanthology\.org)\/\S+|arxiv:\s*\d{4}\.\d{4,5}(v\d+)?|\d{4}\.\d{4,5}(v\d+)?)$/i;
    const PAPER_MAX_BYTES = 20 * 1024 * 1024;
    const paperPopover = document.getElementById('paper-popover');
    const paperQuery = document.getElementById('paper-query');
    const paperBadge = document.getElementById('paper-badge');
    let paperCard = null;

    function findPaper() {
        const query = paperQuery.value.trim();
        if (!query) return;
        paperQuery.value = '';
        requestPaper({ query });
    }

    let pendingPaper = null;

    function requestPaper(payload) {
        paperPopover.style.display = 'none';
        if (socket && socket.readyState === WebSocket.OPEN) {
            showPaperStatus({ state: 'loading', name: payload.name || payload.query || payload.url });
            socket.send(JSON.stringify({ paperRequest: payload }));
        } else {
            // kept until the session is ready, so that a paper chosen before connecting is not lost
            pendingPaper = payload;
            showPaperStatus({ state: 'loading', name: payload.name || payload.query || payload.url });
            appendMessage("System", "The paper will be read as soon as you are connected. Click Connect.", 'system');
        }
    }

    function sendPendingPaper() {
        if (!pendingPaper || !socket || socket.readyState !== WebSocket.OPEN) return;
        socket.send(JSON.stringify({ paperRequest: pendingPaper }));
        pendingPaper = null;
    }

    function showPaperStatus(status) {
        // the card is shown as soon as the paper is requested, then updated by the backend
        const reading = paperCard && paperCard.isConnected && paperCard.classList.contains('pending');
        if (!reading) {
            paperCard = document.createElement('div');
            paperCard.className = 'message paper-card';
            chatLog.appendChild(paperCard);
            lastSpeaker = null;
            lastMessageEl = null;
        }
        paperCard.innerHTML = '';
        paperCard.classList.toggle('pending', status.state === 'loading');
        paperCard.classList.toggle('failed', status.state === 'failed');
        const header = document.createElement('div');
        header.className = 'media-header';
        const icon = document.createElement('span');
        icon.className = 'material-icons';
        icon.textContent = 'description';
        const label = document.createElement('span');
        label.textContent = status.state === 'loading' ? `Reading ${status.name}`
            : status.state === 'failed' ? 'The paper could not be loaded' : 'Paper loaded';
        header.append(icon, label);
        paperCard.appendChild(header);
        const add = (tag, className, text) => {
            if (!text) return;
            const node = document.createElement(tag);
            node.className = className;
            node.textContent = text;
            paperCard.appendChild(node);
        };
        if (status.state === 'loading') {
            if (status.model && !activities.has('paper')) {
                startActivity({ id: 'paper', kind: 'paper', tool: 'load_paper', model: status.model });
            }
        } else if (status.state === 'failed') {
            finishActivity('paper', 'failed');
            add('p', 'paper-text', status.message);
        } else {
            finishActivity('paper', 'done', status.durationMs);
            paperBadge.textContent = status.title;
            paperBadge.title = `Paper loaded: ${status.title}`;
            paperBadge.style.display = 'inline-block';
            add('h4', 'paper-title', status.title);
            add('p', 'paper-text', status.summary);
            const list = document.createElement('ul');
            list.className = 'paper-points';
            for (const point of status.keyPoints || []) {
                const item = document.createElement('li');
                item.textContent = point;
                list.appendChild(item);
            }
            if (list.children.length) paperCard.appendChild(list);
            const count = status.figureCount ? `This paper has ${status.figureCount} figures. ` : '';
            add('p', 'paper-hint', `${count}Ask to see or to try any figure, table, equation or section by name.`);
            add('p', 'paper-source', status.foundWith ? `Found with ${status.foundWith}` : '');
        }
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        initAudioContext();
        appendMessage("You", text, 'user', false);
        userInput.value = '';

        // a link to a paper is loaded by the backend, not sent to the avatar as text
        if (PAPER_LINK.test(text)) {
            requestPaper({ url: text });
            return;
        }

        const clientMessage = {
            realtimeInput: {
                text: text
            }
        };

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(clientMessage));
        } else {
            appendMessage("System", "Not connected to backend.", 'system');
        }
    }

    async function toggleMicrophone() {
        initAudioContext();
        if (isRecording) {
            stopMicrophone();
        } else {
            startMicrophone();
        }
    }

    async function startMicrophone() {
        try {
            micStream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
            micAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
            const source = micAudioContext.createMediaStreamSource(micStream);
            
            // Using ScriptProcessorNode to capture raw PCM audio (1024 samples @ 16kHz = 64ms chunks, within 20-100ms optimal window)
            micProcessor = micAudioContext.createScriptProcessor(1024, 1, 1);
            
            let sentChunks = 0;
            micProcessor.onaudioprocess = (e) => {
                if (!socket || socket.readyState !== WebSocket.OPEN) return;
                sentChunks += 1;
                if (sentChunks === 1 || sentChunks % 100 === 0) console.log(`Sent ${sentChunks} audio chunks`);
                
                const float32Array = e.inputBuffer.getChannelData(0);
                const int16Array = new Int16Array(float32Array.length);
                
                for (let i = 0; i < float32Array.length; i++) {
                    const s = Math.max(-1, Math.min(1, float32Array[i]));
                    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                const uint8Array = new Uint8Array(int16Array.buffer);
                let binaryString = "";
                for (let i = 0; i < uint8Array.length; i += 4096) {
                    const chunk = uint8Array.subarray(i, i + 4096);
                    binaryString += String.fromCharCode.apply(null, chunk);
                }
                const base64Data = btoa(binaryString);
                
                const message = {
                    realtimeInput: {
                        audio: {
                            mimeType: "audio/pcm;rate=16000",
                            data: base64Data
                        }
                    }
                };
                socket.send(JSON.stringify(message));
            };
            
            source.connect(micProcessor);
            micProcessor.connect(micAudioContext.destination);
            
            isRecording = true;
            micBtn.classList.add("active");
            const trackSettings = micStream.getAudioTracks()[0]?.getSettings() || {};
            console.log(`Microphone on: context ${micAudioContext.sampleRate} Hz, track ${trackSettings.sampleRate || '?'} Hz, state ${micAudioContext.state}`);
            appendMessage("System", "Microphone on. Speak, then pause so the avatar can answer.", "system", false);
        } catch (err) {
            console.error("Error accessing microphone:", err);
            appendMessage("System", "Could not access microphone.", "system");
        }
    }

    function stopMicrophone() {
        if (micStream) {
            micStream.getTracks().forEach(track => track.stop());
            micStream = null;
        }
        if (micProcessor) {
            micProcessor.disconnect();
            micProcessor = null;
        }
        if (micAudioContext) {
            micAudioContext.close();
            micAudioContext = null;
        }
        if (isRecording) appendMessage("System", "Microphone off.", "system", false);
        isRecording = false;
        micBtn.classList.remove("active");
    }

    async function toggleVideoInput(source) {
        if (videoSource === source) {
            stopVideoInput();
            return;
        }
        stopVideoInput();
        try {
            videoStream = source === 'screen'
                ? await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
                : await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
        } catch (err) {
            console.error(`Could not start ${source}:`, err);
            appendMessage("System", source === 'screen' ? "Could not share the screen." : "Could not access the camera.", "system", false);
            return;
        }
        videoSource = source;
        inputPreview.srcObject = videoStream;
        inputPreview.style.display = 'block';
        (source === 'screen' ? screenBtn : cameraBtn).classList.add('sharing');
        videoStream.getVideoTracks()[0].addEventListener('ended', stopVideoInput);
        frameTimer = setInterval(sendVideoFrame, FRAME_INTERVAL_MS);
        appendMessage("System", source === 'screen' ? "Screen sharing on. The avatar can see your screen." : "Camera on. The avatar can see your camera.", "system", false);
    }

    function sendVideoFrame() {
        if (!socket || socket.readyState !== WebSocket.OPEN || !inputPreview.videoWidth) return;
        const scale = Math.min(1, FRAME_MAX_SIDE / Math.max(inputPreview.videoWidth, inputPreview.videoHeight));
        frameCanvas.width = Math.round(inputPreview.videoWidth * scale);
        frameCanvas.height = Math.round(inputPreview.videoHeight * scale);
        frameCanvas.getContext('2d').drawImage(inputPreview, 0, 0, frameCanvas.width, frameCanvas.height);
        const base64Data = frameCanvas.toDataURL('image/jpeg', 0.8).split(',')[1];
        socket.send(JSON.stringify({
            realtimeInput: {
                video: {
                    mimeType: "image/jpeg",
                    data: base64Data
                }
            }
        }));
    }

    function stopVideoInput() {
        if (frameTimer) {
            clearInterval(frameTimer);
            frameTimer = null;
        }
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
        }
        inputPreview.srcObject = null;
        inputPreview.style.display = 'none';
        cameraBtn.classList.remove('sharing');
        screenBtn.classList.remove('sharing');
        if (videoSource) appendMessage("System", videoSource === 'screen' ? "Screen sharing off." : "Camera off.", "system", false);
        videoSource = null;
    }

    function handleServerMessage(message) {
        if (message.error) {
            appendMessage("System", `Error: ${message.error}`, 'system', false);
            return;
        }
        if (message.setupComplete || message.setup_complete) {
            statusBadge.textContent = "Connected";
            sendModes();
            sendPendingPaper();
            return;
        }

        // Tool calls from the model: show a pending card while the backend generates the media
        const toolCall = message.toolCall || message.tool_call;
        if (toolCall) {
            const calls = toolCall.functionCalls || toolCall.function_calls || [];
            for (const call of calls) {
                const args = call.args || {};
                if (call.name === 'generate_image') createMediaCard(call.id, 'image', args.prompt || '');
                else if (call.name === 'generate_video') createMediaCard(call.id, 'video', args.prompt || '');
                else if (call.name === 'edit_image') createMediaCard(call.id, 'image', `Edit: ${args.instruction || ''}`);
                else if (call.name === 'edit_video') createMediaCard(call.id, 'video', `Edit: ${args.instruction || ''}`);
                else if (call.name === 'generate_interactive_scene') createMediaCard(call.id, 'scene', args.description || '');
                else if (call.name === 'generate_illustrated_scene') createMediaCard(call.id, 'scene', args.subject || '');
                else if (call.name === 'edit_interactive_scene') createMediaCard(call.id, 'scene', `Edit: ${args.instruction || ''}`);
                else if (call.name === 'annotate_current_view') createMediaCard(call.id, 'image', args.request || args.instruction || '');
            }
            return;
        }

        if (message.paperStatus) {
            showPaperStatus(message.paperStatus);
            return;
        }
        if (message.activityDone) {
            finishActivity(message.activityDone.id, 'done', message.activityDone.durationMs);
            return;
        }
        if (message.generationStarted) {
            startActivity(message.generationStarted);
            return;
        }

        // Results pushed by the backend once a generation finished
        if (message.generatedMedia) {
            showGeneratedMedia(message.generatedMedia);
            return;
        }
        if (message.generationError && message.generationError.kind === 'paper') {
            finishActivity(message.generationError.id, 'failed');
            return;
        }
        if (message.generationError) {
            showGenerationError(message.generationError);
            return;
        }

        const serverContent = message.serverContent || message.server_content;
        if (!serverContent) return;

        const inputTranscription = serverContent.inputTranscription || serverContent.input_transcription;
        if (inputTranscription && inputTranscription.text) {
            appendMessage("You (Spoken)", inputTranscription.text, 'user', true);
        }

        const outputTranscription = serverContent.outputTranscription || serverContent.output_transcription;
        if (outputTranscription && outputTranscription.text) {
            appendMessage("Avatar (Transcript)", outputTranscription.text, 'model', true);
        }

        if (serverContent.interrupted) {
            console.log("Model interrupted.");
            stopAudio();
            flushAvatarVideo();
            lastSpeaker = null;
            lastMessageEl = null;
            return;
        }

        const turnComplete = Boolean(serverContent.turnComplete || serverContent.turn_complete);
        const modelTurn = serverContent.modelTurn || serverContent.model_turn;
        if (modelTurn && modelTurn.parts) {
            for (const part of modelTurn.parts) {
                if (part.text) {
                    appendMessage("Avatar", part.text, 'model', true);
                } else {
                    const inlineData = part.inlineData || part.inline_data || part.video;
                    if (inlineData) {
                        const mimeType = inlineData.mimeType || inlineData.mime_type;
                        const data = inlineData.data;

                        if (mimeType && mimeType.startsWith('image/')) {
                            avatarImage.src = `data:${mimeType};base64,${data}`;
                        } else if (mimeType && mimeType.startsWith('video/')) {
                            const arrayBuffer = base64ToArrayBuffer(data);
                            videoQueue.push(arrayBuffer);
                            processVideoQueue();
                        } else if (mimeType && mimeType.startsWith('audio/')) {
                            queueAudioFrame(mimeType, data);
                        } else if (!mimeType && !part.video) {
                            queueAudioFrame('audio/pcm', data);
                        }
                    }
                }
            }
        }

        if (turnComplete) {
            flushPrebuffer(true);
        }
    }

    function connect() {
        if (socket && socket.readyState !== WebSocket.CLOSED) return;

        initAudioContext();
        if (avatarVideo) avatarVideo.muted = true;

        statusBadge.textContent = "Connecting...";
        statusBadge.className = "badge";
        showPlaceholder(true);

        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const query = `?avatar=${encodeURIComponent(avatarSelect.value)}&voice=${encodeURIComponent(voiceSelect.value)}`;
        const wsUrl = wsProtocol + (window.location.host || 'localhost:8080') + '/' + query;
        console.log(`Connecting to ${wsUrl}...`);
        
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log("WebSocket connected to backend.");
            statusBadge.textContent = "Starting";
            statusBadge.className = "badge connected";
            
            connectBtn.style.display = 'none';
            disconnectBtn.style.display = 'block';
            
            userInput.disabled = false;
            sendBtn.disabled = false;
            micBtn.disabled = false;
            cameraBtn.disabled = false;
            screenBtn.disabled = false;
            paperBtn.disabled = false;
            
            initMediaSource();
            
            if (avatarPlaceholder) avatarPlaceholder.style.display = 'none';
            if (avatarVideo) {
                avatarVideo.style.display = 'block';
            }
            
            document.body.addEventListener('click', () => {
                initAudioContext();
                if (avatarVideo) avatarVideo.muted = true;
            }, { once: true });
        };

        socket.onmessage = (event) => {
            if (typeof event.data === 'string') {
                try {
                    const message = JSON.parse(event.data);
                    handleServerMessage(message);
                } catch (err) {
                    console.error("Error parsing JSON message:", err);
                }
            }
        };

        socket.onclose = () => {
            console.log("WebSocket disconnected.");
            handleDisconnectState();
            if (reconnectAfterClose) {
                reconnectAfterClose = false;
                connect();
            }
        };

        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
            handleDisconnectState();
        };
    }

    function disconnect() {
        if (socket) {
            socket.close();
        }
        stopMicrophone();
        stopVideoInput();
        handleDisconnectState();
    }

    function handleDisconnectState() {
        statusBadge.textContent = "Disconnected";
        statusBadge.className = "badge disconnected";
        
        connectBtn.style.display = 'block';
        disconnectBtn.style.display = 'none';
        
        userInput.disabled = true;
        sendBtn.disabled = true;
        micBtn.disabled = true;
        cameraBtn.disabled = true;
        screenBtn.disabled = true;
        paperBtn.disabled = true;
        stopVideoInput();
        
        showPlaceholder(false);
        if (avatarVideo) avatarVideo.style.display = 'none';
        
        stopAudio();
    }

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    connectBtn.addEventListener('click', connect);
    disconnectBtn.addEventListener('click', disconnect);
    resetBtn.addEventListener('click', resetSession);
    paperBtn.addEventListener('click', () => {
        const open = paperPopover.style.display === 'none';
        paperPopover.style.display = open ? 'flex' : 'none';
        if (open) paperQuery.focus();
    });
    document.getElementById('paper-upload-btn').addEventListener('click', () => paperFile.click());
    document.getElementById('paper-find-btn').addEventListener('click', findPaper);
    paperQuery.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') findPaper();
        if (e.key === 'Escape') paperPopover.style.display = 'none';
    });
    // suggestions on the empty stage
    paperFile.addEventListener('change', async () => {
        const files = Array.from(paperFile.files);
        paperFile.value = '';
        paperPopover.style.display = 'none';
        for (const file of files) {
            if (file.type.startsWith('image/')) {
                await addUpload(file);
            } else if (file.size > PAPER_MAX_BYTES) {
                appendMessage("System", `${file.name} is larger than 20 MB.`, 'system');
            } else if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                appendMessage("System", `${file.name} is not a PDF. Papers must be PDF files; pictures can be added as images.`, 'system');
            } else {
                const reader = new FileReader();
                reader.onload = () => requestPaper({ name: file.name, data: String(reader.result).split(',')[1] });
                reader.onerror = () => appendMessage("System", `${file.name} could not be read from disk. Try again.`, 'system');
                reader.readAsDataURL(file);
            }
        }
    });
    // the Results link appears once eval/run_eval.py has written its report page
    fetch('results.html').then((response) => {
        if (response.ok) document.getElementById('results-link').style.display = 'inline-block';
    }).catch(() => {});
    
    micBtn.addEventListener('click', toggleMicrophone);
    avatarSelect.addEventListener('change', onTeacherChange);
    voiceSelect.addEventListener('change', onTeacherChange);
    populateTeacherPicker();
    cameraBtn.addEventListener('click', () => toggleVideoInput('camera'));
    screenBtn.addEventListener('click', () => toggleVideoInput('screen'));

    // Artifacts Pane & Lightbox Event Listeners
    if (artifactsToggleBtn) artifactsToggleBtn.addEventListener('click', toggleArtifactsPane);
    if (artifactsCloseBtn) artifactsCloseBtn.addEventListener('click', minimizeArtifactsPane);
    if (artifactsExpandBtn) artifactsExpandBtn.addEventListener('click', expandArtifactsPane);
    if (lightboxCloseBtn) lightboxCloseBtn.addEventListener('click', closeLightbox);
    if (lightboxBackdrop) lightboxBackdrop.addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && mediaLightbox && mediaLightbox.style.display !== 'none') {
            closeLightbox();
        }
        if (e.key === 'Escape') featuredMediaWrapper.parentElement.classList.remove('scene-expanded');
    });
    if (featuredCopyBtn) {
        featuredCopyBtn.addEventListener('click', () => {
            const active = artifactsMap.get(activeArtifactId);
            if (active && active.prompt) {
                navigator.clipboard.writeText(active.prompt).then(() => {
                    if (featuredCopyText) featuredCopyText.textContent = 'Copied!';
                    setTimeout(() => {
                        if (featuredCopyText) featuredCopyText.textContent = 'Copy';
                    }, 1500);
                }).catch(() => {});
            }
        });
    }
});