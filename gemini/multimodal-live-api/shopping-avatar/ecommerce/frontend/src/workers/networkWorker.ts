import { 
    GoogleGenAI, 
    Modality, 
    type Session, 
    type LiveServerMessage, 
    type LiveConnectConfig,
    type Content,
    type GoogleGenAIOptions,
} from '@google/genai';

let session: Session | null = null;
let modelName = '';
let isIgnoringTrailingChunks = false;
let hasLoggedFirstAudioChunk = false;
let isSetupComplete = false;
const processedToolCallIds = new Set<string>();

const workerPostMessage = (self as unknown as Worker).postMessage.bind(self);

const processToolCall = (name: string, args: Record<string, unknown>, id: string) => {
    if (processedToolCallIds.has(id)) return;
    processedToolCallIds.add(id);
    workerPostMessage({ 
        type: 'TOOL_CALL', 
        payload: { 
            functionCall: { name, args, id } 
        } 
    });
};

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

const buildLiveConnectConfig = (payload: {
    systemPrompt: string;
    tools: import('@google/genai').FunctionDeclaration[];
    useVertexAI: boolean;
    avatarMode: string;
    google1PAvatarName?: string;
    google1PVoiceName?: string;
    vadSilenceDurationMs?: number;
}): LiveConnectConfig => {
    const baseConfig: LiveConnectConfig = {
        systemInstruction: { parts: [{ text: payload.systemPrompt }] } as Content,
        tools: payload.tools.length > 0 ? [{
            functionDeclarations: payload.useVertexAI 
                ? (payload.tools as unknown as Record<string, unknown>[]).map((t: Record<string, unknown>) => ({
                    ...t,
                    parameters: t.parameters 
                        ? JSON.parse(JSON.stringify(t.parameters).replace(/"type":"([a-z]+)"/g, (_m, p1) => `"type":"${p1.toUpperCase()}"`)) 
                        : undefined
                })) 
                : payload.tools
        }] : undefined
    };

    let voiceName = payload.google1PVoiceName || "Aoede";
    const speechConfig = { 
        voiceConfig: { prebuiltVoiceConfig: { voiceName } } 
    };

    if (payload.avatarMode === 'google_1p' && payload.useVertexAI) {
        return {
            ...baseConfig,
            speechConfig,
            responseModalities: [Modality.AUDIO, "VIDEO" as unknown as Modality],
            outputAudioTranscription: {},
            inputAudioTranscription: {},
            avatarConfig: {
                avatarName: payload.google1PAvatarName || "Vera"
            }
        };
    }

    return {
        ...baseConfig,
        speechConfig,
        responseModalities: [Modality.AUDIO],
        outputAudioTranscription: {},
        inputAudioTranscription: {},
    };
};

self.onmessage = async (event) => {
    const { type, payload } = event.data;

    switch (type) {
        case 'INITIALIZE':
            try {
                modelName = payload.modelName;
                isIgnoringTrailingChunks = false;
                hasLoggedFirstAudioChunk = false;
                isSetupComplete = false;

                const aiConfig: GoogleGenAIOptions = {
                    apiKey: payload.useVertexAI ? 'proxy' : (payload.apiKey || 'dummy'),
                    ...(payload.useVertexAI && {
                        vertexai: true,
                        httpOptions: {
                            baseUrl: `${self.location.origin}/api/live-avatar`,
                        }
                    })
                };

                const ai = new GoogleGenAI(aiConfig);
                
                if (payload.useVertexAI) {
                    const patchedAi = ai as unknown as import('@google/genai').GoogleGenAIPatch;
                    patchedAi.apiClient.isVertexAI = () => true;
                    patchedAi.apiClient.getProject = () => payload.vertexProject || "proxy";
                    patchedAi.apiClient.getLocation = () => payload.vertexLocation || "proxy";
                }

                const config = buildLiveConnectConfig(payload);

                const connectParams = {
                    model: modelName,
                    config: config,
                    callbacks: {
                        onopen: () => {
                            console.log('[NetworkWorker] Socket opened');
                        },
                        onclose: (event: CloseEvent) => {
                            console.log(`[NetworkWorker] Socket closed. Code: ${event?.code}, Reason: ${event?.reason}`);
                            isSetupComplete = false;
                            workerPostMessage({ type: 'STATE_CHANGE', payload: 'disconnected', code: event?.code, reason: event?.reason });
                        },
                        onmessage: (msg: LiveServerMessage) => handleMessage(msg),
                        onerror: (err: unknown) => {
                            console.error('[NetworkWorker] SDK Error:', err);
                            workerPostMessage({ type: 'STATE_CHANGE', payload: 'error', error: String(err) });
                        }
                    }
                };

                session = await ai.live.connect(connectParams);
                setTimeout(() => {
                    if (!isSetupComplete && session) {
                        console.log('[NetworkWorker] Fallback 1500ms timer marked setup complete');
                        isSetupComplete = true;
                        workerPostMessage({ type: 'STATE_CHANGE', payload: 'connected' });
                    }
                }, 1500);
            } catch (err: unknown) {
                console.error('[NetworkWorker] Connection failed:', err);
                workerPostMessage({ type: 'STATE_CHANGE', payload: 'error', error: err instanceof Error ? err.message : String(err) });
            }
            break;

        case 'SEND_AUDIO':
            if (session && isSetupComplete) {
                if (!hasLoggedFirstAudioChunk) {
                    console.log('[NetworkWorker] Forwarding first audio chunk to Gemini');
                    hasLoggedFirstAudioChunk = true;
                }
                session.sendRealtimeInput({ 
                    audio: { 
                        data: arrayBufferToBase64(payload as ArrayBuffer), 
                        mimeType: 'audio/pcm;rate=16000' 
                    }
                });
            }
            break;

        case 'SEND_VIDEO':
            if (session && isSetupComplete) {
                session.sendRealtimeInput({
                    video: {
                        data: payload.data,
                        mimeType: payload.mimeType
                    }
                });
            }
            break;


        case 'SEND_TEXT':
            if (session && isSetupComplete) {
                session.sendRealtimeInput({ 
                    text: payload
                });
            }
            break;


        case 'TOOL_RESPONSE':
            if (session) {
                const respObj = (payload.result && typeof payload.result === 'object') ? (payload.result as Record<string, unknown>) : {};
                session.sendToolResponse({ 
                    functionResponses: [{ 
                        id: payload.id, 
                        name: payload.toolName,
                        response: respObj
                    }] 
                });
            }
            break;

        case 'DISCONNECT':
            if (session) {
                session.close();
                session = null;
            }
            workerPostMessage({ type: 'STATE_CHANGE', payload: 'disconnected' });
            break;
    }
};

const handleMessage = (msg: LiveServerMessage) => {
    try {
      if (msg.setupComplete) {
        console.log('[NetworkWorker] Setup complete received from Live API');
        isSetupComplete = true;
        workerPostMessage({ type: 'STATE_CHANGE', payload: 'connected' });
      }

      let isInterruptedInThisMessage = false;
      if (msg.serverContent?.interrupted) {
        isIgnoringTrailingChunks = true;
        isInterruptedInThisMessage = true;
        workerPostMessage({ type: 'INTERRUPTED' });
      }

      if (msg.serverContent?.inputTranscription) {
        isIgnoringTrailingChunks = false;
        workerPostMessage({ 
            type: 'TRANSCRIPTION', 
            payload: { 
                text: msg.serverContent.inputTranscription.text, 
                type: 'input',
                finished: msg.serverContent.inputTranscription.finished
            } 
        });
      }

      const serverContent = msg.serverContent || (msg as any).server_content;
      const modelTurn = serverContent?.modelTurn || (serverContent as any)?.model_turn;

      if (modelTurn?.parts) {
        if (!isInterruptedInThisMessage) {
            const hasNewTurnIndicator = modelTurn.parts.some((p: any) => p.text || p.functionCall || p.function_call);
            if (hasNewTurnIndicator) {
                isIgnoringTrailingChunks = false;
            }
        }

        modelTurn.parts.forEach((part: any) => {
          const inlineData = part.inlineData || part.inline_data;
          if (inlineData?.data) {
            if (isIgnoringTrailingChunks) return;

            const base64Data = inlineData.data;
            const mimeType = inlineData.mimeType || inlineData.mime_type || '';

            if (mimeType.startsWith('audio/')) {
                const binaryString = atob(base64Data);
                const uint8Array = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    uint8Array[i] = binaryString.charCodeAt(i);
                }
                const pcmData = new Int16Array(uint8Array.buffer);
                const floatData = new Float32Array(pcmData.length);
                for (let i = 0; i < pcmData.length; i++) {
                    floatData[i] = pcmData[i] / 32768.0;
                }

                workerPostMessage({ 
                    type: 'AUDIO_DATA', 
                    payload: {
                        base64: base64Data,
                        buffer: floatData.buffer
                    } 
                }, [floatData.buffer]);
            } else if (mimeType.startsWith('video/') || mimeType.startsWith('image/') || mimeType === '') {
                workerPostMessage({ 
                    type: 'VIDEO_DATA', 
                    payload: base64Data
                });
            }
          }
          if (part.text) {
              workerPostMessage({
                  type: 'TRANSCRIPTION',
                  payload: {
                      text: part.text,
                      type: 'output'
                  }
              });
          }
          const functionCall = part.functionCall || part.function_call;
          if (functionCall) {
            processToolCall(
                functionCall.name || '', 
                (functionCall.args as Record<string, unknown>) || {}, 
                functionCall.id || ''
            );
          }
        });
      }


      if (msg.toolCall?.functionCalls) {
        msg.toolCall.functionCalls.forEach((call) => {
          processToolCall(
              call.name || '',
              (call.args as Record<string, unknown>) || {},
              call.id || call.name || ''
          );
        });
      }

      if (msg.serverContent?.turnComplete) {
        isIgnoringTrailingChunks = false;
        hasLoggedFirstAudioChunk = false;
        workerPostMessage({ type: 'TURN_COMPLETE' });
      }

      if (msg.serverContent?.outputTranscription) {
          workerPostMessage({ 
            type: 'TRANSCRIPTION', 
            payload: { 
                text: msg.serverContent.outputTranscription.text, 
                type: 'output',
                finished: msg.serverContent.outputTranscription.finished
            } 
        });
      }

    } catch (err) {
      console.error('[NetworkWorker] Error handling message:', err);
    }
};
