class LiveAudioOutputManager {
    constructor() {
        this.audioInputContext;
        this.workletNode;
        this.initialized = false;

        this.audioQueue = [];
        this.isPlaying = false;

        this.initializeAudioContext();
    }

    async playAudioChunk(base64AudioChunk) {
        try {
            if (!this.initialized) {
                await this.initializeAudioContext();
            }

            if (this.audioInputContext.state === "suspended") {
                await this.audioInputContext.resume();
            }

            const arrayBuffer =
                LiveAudioOutputManager.base64ToArrayBuffer(base64AudioChunk);
            const float32Data =
                LiveAudioOutputManager.convertPCM16LEToFloat32(arrayBuffer);

            this.workletNode.port.postMessage(float32Data);
        } catch (error) {
            console.error("Error processing audio chunk:", error);
        }
    }

    async initializeAudioContext() {
        if (this.initialized) return;

        console.log("initializeAudioContext...");

        this.audioInputContext = new (window.AudioContext ||
            window.webkitAudioContext)({ sampleRate: 24000 });
        await this.audioInputContext.audioWorklet.addModule("pcm-processor.js");
        this.workletNode = new AudioWorkletNode(
            this.audioInputContext,
            "pcm-processor",
        );
        this.workletNode.connect(this.audioInputContext.destination);

        this.initialized = true;
        console.log("initializeAudioContext end");
    }

    static base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }

    static convertPCM16LEToFloat32(pcmData) {
        const inputArray = new Int16Array(pcmData);
        const float32Array = new Float32Array(inputArray.length);
        for (let i = 0; i < inputArray.length; i++) {
            float32Array[i] = inputArray[i] / 32768;
        }
        return float32Array;
    }
}

class LiveAudioInputManager {
    constructor() {
        this.audioContext;
        this.mediaRecorder;
        this.processor = null;
        this.pcmData = [];

        this.deviceId = null;

        this.interval = null;
        this.stream = null;

        this.onNewAudioRecordingChunk = (audioData) => {
            console.log("New audio recording ");
        };
    }

    async connectMicrophone() {
        this.audioContext = new AudioContext({
            sampleRate: 16000,
        });

        let constraints = {
            audio: {
                channelCount: 1,
                sampleRate: 16000,
            },
        };

        if (this.deviceId) {
            constraints.audio.deviceId = { exact: this.deviceId };
        }

        this.stream = await navigator.mediaDevices.getUserMedia(constraints);

        const source = this.audioContext.createMediaStreamSource(this.stream);
        // Load the worklet module.
        await this.audioContext.audioWorklet.addModule('input-processor.js');

        // Create an AudioWorkletNode.
        this.processor = new AudioWorkletNode(this.audioContext, 'input-processor');

        // Listen for messages (the PCM data) from the worklet.
        this.processor.port.onmessage = (event) => {
            this.pcmData.push(...event.data);
        };

        // Connect the microphone source to the worklet.
        source.connect(this.processor);
        // this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

        // this.processor.onaudioprocess = (e) => {
        //     console.log("Audio data received from microphone.");
        //     const inputData = e.inputBuffer.getChannelData(0);
        //     // Convert float32 to int16
        //     const pcm16 = new Int16Array(inputData.length);
        //     for (let i = 0; i < inputData.length; i++) {
        //         pcm16[i] = inputData[i] * 0x7fff;
        //     }
        //     this.pcmData.push(...pcm16);
        // };

        // source.connect(this.processor);
        // this.processor.connect(this.audioContext.destination);

        this.interval = setInterval(this.recordChunk.bind(this), 1000);
    }

    newAudioRecording(b64AudioData) {
        console.log("newAudioRecording ");
        this.onNewAudioRecordingChunk(b64AudioData);
    }

    recordChunk() {
        const buffer = new ArrayBuffer(this.pcmData.length * 2);
        const view = new DataView(buffer);
        this.pcmData.forEach((value, index) => {
            view.setInt16(index * 2, value, true);
        });

        const base64 = btoa(
            String.fromCharCode.apply(null, new Uint8Array(buffer)),
        );
        this.newAudioRecording(base64);
        this.pcmData = [];
    }

    disconnectMicrophone() {
        try {
            if (this.stream) {
                this.stream.getTracks().forEach((track) => {
                    track.stop();
                });
            }
            if (this.processor) {
                this.processor.disconnect();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            console.log("Microphone disconnected successfully.");
        } catch {
            console.error("Error disconnecting microphone");
        }

        clearInterval(this.interval);
    }

    async updateMicrophoneDevice(deviceId) {
        this.deviceId = deviceId;
        this.disconnectMicrophone();
        await this.connectMicrophone();
    }
}

class LiveVideoManager {
    constructor(previewVideoElement, previewCanvasElement) {
        this.previewVideoElement = previewVideoElement;
        this.previewCanvasElement = previewCanvasElement;
        this.ctx = this.previewCanvasElement.getContext("2d");
        this.stream = null;
        this.interval = null;
        this.deviceId = null;
        this.onNewFrame = (newFrame) => {
            console.log("Default new frame trigger.");
        };
    }

    async startWebcam() {
        if (this.stream) {
            return; // Already started
        }
        try {
            const constraints = {
                video: { deviceId: this.deviceId ? { exact: this.deviceId } : undefined }
                // video: {
                //     width: { max: 640 },
                //     height: { max: 480 },
                // },
            };
            this.stream =
                await navigator.mediaDevices.getUserMedia(constraints);
            this.previewVideoElement.srcObject = this.stream;
            this.interval = setInterval(() => { this.onNewFrame() }, 1000);
        } catch (err) {
            console.error("Error accessing the webcam: ", err);
        }

        // setInterval(this.newFrame.bind(this), 10000);
    }

    stopWebcam() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        if (this.stream) {
            this.stopStream();
            this.stream = null;
        }
    }

    stopStream() {
        if (!this.stream) return;

        const tracks = this.stream.getTracks();

        tracks.forEach((track) => {
            track.stop();
        });
    }

    async updateWebcamDevice(deviceId) {
        this.deviceId = deviceId;
        this.stopWebcam();
        await this.startWebcam();
        // const constraints = {
        //     video: { deviceId: { exact: deviceId } },
        // };
        // this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        // this.previewVideoElement.srcObject = this.stream;
    }

    captureFrameB64() {
        if (this.stream == null) return "";

        this.previewCanvasElement.width = this.previewVideoElement.videoWidth;
        this.previewCanvasElement.height = this.previewVideoElement.videoHeight;
        this.ctx.drawImage(
            this.previewVideoElement,
            0,
            0,
            this.previewCanvasElement.width,
            this.previewCanvasElement.height,
        );
        const imageData = this.previewCanvasElement
            .toDataURL("image/jpeg")
            .split(",")[1]
            .trim();
        return imageData;
    }

    newFrame() {
        console.log("capturing new frame");
        const frameData = this.captureFrameB64();
        this.onNewFrame(frameData);
    }
}

class LiveScreenManager {
    constructor(previewVideoElement, previewCanvasElement) {
        this.previewVideoElement = previewVideoElement;
        this.previewCanvasElement = previewCanvasElement;
        this.ctx = this.previewCanvasElement.getContext("2d");
        this.stream = null;
        this.interval = null;
        this.onNewFrame = (newFrame) => {
            console.log("Default new frame trigger: ", newFrame);
        };
    }

    async startCapture() {
        if (this.interval) {
            clearInterval(this.interval);
        }

        try {
            console.log("Starting screen capture...");
            this.stream = await navigator.mediaDevices.getDisplayMedia();
            this.previewVideoElement.srcObject = this.stream;

            this.interval = setInterval(this.newFrame.bind(this), 1000);
        } catch (err) {
            console.error("Error accessing the webcam: ", err);
        }
    }

    stopCapture() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }

        if (!this.stream) return;

        const tracks = this.stream.getTracks();

        tracks.forEach((track) => {
            track.stop();
        });

        this.previewVideoElement.srcObject = null;
        this.stream = null;
    }

    captureFrameB64() {
        if (this.stream == null) return "";

        this.previewCanvasElement.width = this.previewVideoElement.videoWidth;
        this.previewCanvasElement.height = this.previewVideoElement.videoHeight;
        this.ctx.drawImage(
            this.previewVideoElement,
            0,
            0,
            this.previewCanvasElement.width,
            this.previewCanvasElement.height,
        );
        const imageData = this.previewCanvasElement
            .toDataURL("image/jpeg")
            .split(",")[1]
            .trim();
        return imageData;
    }

    newFrame() {
        console.log("capturing new frame");
        const frameData = this.captureFrameB64();
        this.onNewFrame(frameData);
    }
}

console.log("loaded live-media-manager.js");
