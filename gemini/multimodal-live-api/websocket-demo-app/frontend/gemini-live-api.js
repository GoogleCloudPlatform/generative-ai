class GeminiLiveResponseMessage {
    constructor(data) {
        this.data = "";
        this.type = "";
        this.endOfTurn = data?.serverContent?.turnComplete;
        this.interrupt = data?.serverContent?.interrupted;

        const parts = data?.serverContent?.modelTurn?.parts;

        if (data?.setupComplete) {
            this.type = "SETUP COMPLETE";
        } else if (data?.voiceActivityDetectionSignal) {
            this.type = "VAD_SIGNAL";
        } else if (parts?.length && parts[0].text) {
            this.data = parts[0].text;
            this.type = "TEXT";
        } else if (parts?.length && parts[0].inlineData) {
            this.data = parts[0].inlineData.data;
            this.type = "AUDIO";
        } else if (data?.sessionResumptionUpdate) {
            this.type = "RESUMPTION";
            this.data = data?.sessionResumptionUpdate?.newHandle;
        } else if (data?.serverContent?.inputTranscription) {
            this.type = "INPUT_TRANSCRIPTION";
            if (data?.serverContent?.inputTranscription?.text) {
                this.data = data?.serverContent?.inputTranscription?.text;
            } else if (data?.serverContent?.inputTranscription?.finished) {
                this.data = data?.serverContent?.inputTranscription?.finished
            }
        } else if (data?.serverContent?.outputTranscription) {
            this.type = "OUTPUT_TRANSCRIPTION";
            if (data?.serverContent?.outputTranscription?.text) {
                this.data = data?.serverContent?.outputTranscription?.text;
            } else if (data?.serverContent?.outputTranscription?.finished) {
                this.data = "Finished: "+data?.serverContent?.outputTranscription?.finished
            }
        } else if (this.endOfTurn) {
            this.data = "END OF TURN";
            this.type = "END_OF_TURN";
        } else if (this.interrupt) {
            this.data = "INTERRUPT";
            this.type = "INTERRUPT";
        }
    }
}

class GeminiLiveAPI {
    constructor(proxyUrl, projectId, model, apiHost) {
        this.proxyUrl = proxyUrl;

        this.projectId = projectId;
        this.model = model;
        this.modelUri = `projects/${this.projectId}/locations/us-central1/publishers/google/models/${this.model}`;
        console.log("Model URI:", this.modelUri);

        this.responseModalities = ["AUDIO"];
        this.systemInstructions = "";

        this.apiHost = apiHost;
        // this.serviceUrl = `wss://${this.apiHost}/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent`;
        this.serviceUrl = `wss://${this.apiHost}/ws/google.cloud.aiplatform.internal.LlmBidiService/BidiGenerateContent`;

        this.onReceiveResponse = (message) => {
            console.log("Default message received callback", message);
        };

        this.onConnectionStarted = () => {
            console.log("Default onConnectionStarted");
        };

        this.onErrorMessage = (message) => {
            alert(message);
        };

        this.accessToken = "";
        this.websocket = null;

        this.enableInputTranscript = false;
        this.enableOutputTranscript = false;
        this.voiceName = "";
        this.voiceLocale = "";
        this.enableSessionResumption = false;
        this.resumptionHandle = "";
        this.disableDetection = false;
        this.disableInterruption = false;
        this.startSensitivity = "";
        this.endSensitivity = "";
        this.enableProactiveVideo = false;

        console.log("Created Gemini Live API object: ", this);
    }

    setProjectId(projectId) {
        this.projectId = projectId;
        this.modelUri = `projects/${this.projectId}/locations/us-central1/publishers/google/models/${this.model}`;
    }

    setApiHost(apiHost) {
        this.apiHost = apiHost;
    }

    setAccessToken(newAccessToken) {
        console.log("setting access token: ", newAccessToken);
        this.accessToken = newAccessToken;
    }

    setTranscript(input, output) {
        console.log("input transcript: ", input, "output transcript: ", output);
        this.enableInputTranscript = input;
        this.enableOutputTranscript = output;
    }

    setVoice(name, locale) {
        this.voiceName = name;
        this.voiceLocale = locale;
    }

    setResumption(enable, handle) {
        this.enableSessionResumption = enable;
        this.resumptionHandle = handle;
    }

    setVad(disableInterruption, disableDetection, startSen, endSen) {
        this.disableDetection = disableDetection;
        this.disableInterruption = disableInterruption;
        this.startSensitivity = startSen;
        this.endSensitivity = endSen;
    }

    setProactiveVideo(enable) {
        this.enableProactiveVideo = enable;
    }

    connect(accessToken) {
        this.setAccessToken(accessToken);
        this.setupWebSocketToService();
    }

    disconnect() {
        this.webSocket.close();
    }

    sendMessage(message) {
        this.webSocket.send(JSON.stringify(message));
    }

    onReceiveMessage(messageEvent) {
        console.log("Message received: ", messageEvent);
        const messageData = JSON.parse(messageEvent.data);
        const message = new GeminiLiveResponseMessage(messageData);
        console.log("onReceiveMessageCallBack this ", this);
        this.onReceiveResponse(message);
    }

    setupWebSocketToService() {
        console.log("connecting: ", this.proxyUrl);

        this.webSocket = new WebSocket(this.proxyUrl);

        this.webSocket.onclose = (event) => {
            console.log("websocket closed: ", event);
            this.onErrorMessage("Connection closed");
        };

        this.webSocket.onerror = (event) => {
            console.log("websocket error: ", event);
            this.onErrorMessage("Connection error");
        };

        this.webSocket.onopen = (event) => {
            console.log("websocket open: ", event);
            this.sendInitialSetupMessages();
            this.onConnectionStarted();
        };

        this.webSocket.onmessage = this.onReceiveMessage.bind(this);
    }

    sendInitialSetupMessages() {
        const serviceSetupMessage = {
            bearer_token: this.accessToken,
            service_url: this.serviceUrl,
        };
        this.sendMessage(serviceSetupMessage);

        const sessionSetupMessage = {
            setup: {
                model: this.modelUri,
                realtime_input_config: {},
                explicit_vad_signal: true,
                generation_config: {
                    response_modalities: this.responseModalities,
                    speech_config: {
                        voice_config: {
                            prebuilt_voice_config: {voice_name: this.voiceName},
                        },
                        language_code: this.voiceLocale
                    }
                },
            },
        };

        if (this.systemInstructions && this.systemInstructions.trim()) {
            sessionSetupMessage.setup.system_instruction = {
                parts: [{ text: this.systemInstructions }],
            };
        }

        if (this.enableInputTranscript) {
            sessionSetupMessage.setup.input_audio_transcription = {};
        }
        if (this.enableOutputTranscript) {
            sessionSetupMessage.setup.output_audio_transcription = {};
        }
        if (this.enableSessionResumption) {
            sessionSetupMessage.setup.session_resumption = {
                handle: this.resumptionHandle
            };
        }

        sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection = {}
        if (this.disableDetection) {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.disabled = true;
        }
        if (this.disableInterruption) {
            sessionSetupMessage.setup.realtime_input_config.activity_handling = 2;
        }

        if (this.startSensitivity === "") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.start_of_speech_sensitivity = 0;
        } else if (this.startSensitivity === "low") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.start_of_speech_sensitivity = 2;
        } else if (this.startSensitivity === "high") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.start_of_speech_sensitivity = 1;
        }

        if (this.endSensitivity === "") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.end_of_speech_sensitivity = 0;
        } else if (this.endSensitivity === "low") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.end_of_speech_sensitivity = 2;
        } else if (this.endSensitivity === "high") {
            sessionSetupMessage.setup.realtime_input_config.automatic_activity_detection.end_of_speech_sensitivity = 1;
        }

        if (this.enableProactiveVideo) {
            sessionSetupMessage.setup.proactivity = {
                proactive_video: true,
            };
        }

        console.log("setup message: " + sessionSetupMessage);
        this.sendMessage(sessionSetupMessage);
    }

    sendTextMessage(text) {
        const textMessage = {
            client_content: {
                turns: [
                    {
                        role: "user",
                        parts: [{ text: text }],
                    },
                ],
                turn_complete: true,
            },
        };
        this.sendMessage(textMessage);
    }

    sendVoiceActivityMessage(start) {
        if (start) {
            const startMessage = {
                realtime_input: {
                    activity_start: {},
                },
            };
            this.sendMessage(startMessage);
        } else {
            const endMessage = {
                realtime_input: {
                    activity_end: {},
                },
            };
            this.sendMessage(endMessage);
        }
    }

    sendRealtimeInputMessage(data, mime_type) {
        const message = {
            realtime_input: {
                media_chunks: [
                    {
                        mime_type: mime_type,
                        data: data,
                    },
                ],
            },
        };
        this.sendMessage(message);
    }

    sendAudioMessage(base64PCM) {
        this.sendRealtimeInputMessage(base64PCM, "audio/pcm");
    }

    sendImageMessage(base64Image, mime_type = "image/jpeg") {
        this.sendRealtimeInputMessage(base64Image, mime_type);
    }
}

console.log("loaded gemini-live-api.js");
