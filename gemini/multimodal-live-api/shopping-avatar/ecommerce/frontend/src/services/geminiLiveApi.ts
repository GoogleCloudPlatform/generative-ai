import NetworkWorker from '../workers/networkWorker?worker';
import { type MCPTool } from '../api/tools';

export interface ToolCall {
  functionCall: {
    name: string;
    args: Record<string, unknown>;
    id: string;
  };
}

export interface Transcription {
  text: string;
  type: 'input' | 'output';
  finished?: boolean;
}

export interface GeminiLiveApiOptions {
  apiKey: string;
  modelName: string;
  systemPrompt: string;
  mcpTools: MCPTool[];
  useVertexAI: boolean;
  vertexProject: string;
  vertexLocation: string;
  avatarMode: string;
  google1PAvatarName?: string;
  google1PVoiceName?: string;
  onStateChange: (state: 'connected' | 'disconnected' | 'error' | 'connecting') => void;
  onAudioReceived: (payload: { base64: string; buffer: ArrayBuffer }) => void;
  onVideoReceived?: (base64Video: string) => void;
  onToolCall: (toolCall: ToolCall) => void;
  onTranscription: (transcription: Transcription) => void;
  onInterrupted: () => void;
  onTurnComplete?: () => void;
}

export class GeminiLiveApi {
  private worker: Worker | null = null;
  private options: GeminiLiveApiOptions;

  constructor(options: GeminiLiveApiOptions) {
    this.options = options;
  }

  public async connect() {
    try {
        this.worker = new NetworkWorker();

        this.worker.onmessage = (event) => {
            const { type, payload, error } = event.data;

            switch (type) {
                case 'STATE_CHANGE':
                    this.options.onStateChange(payload);
                    if (payload === 'error') {
                        console.error('[GeminiLiveApi] Worker error:', error);
                    }
                    break;
                case 'AUDIO_DATA':
                    this.options.onAudioReceived(payload);
                    break;
                case 'VIDEO_DATA':
                    if (this.options.onVideoReceived) {
                        this.options.onVideoReceived(payload);
                    }
                    break;
                case 'TOOL_CALL':
                    this.options.onToolCall(payload);
                    break;
                case 'TRANSCRIPTION':
                    this.options.onTranscription(payload);
                    break;
                case 'INTERRUPTED':
                    this.options.onInterrupted();
                    break;
                case 'TURN_COMPLETE':
                    if (this.options.onTurnComplete) this.options.onTurnComplete();
                    break;
            }
        };

        const tools = this.options.mcpTools.map(tool => ({
            name: tool.name,
            description: tool.description,
            parameters: tool.inputSchema,
        }));

        this.worker.postMessage({
            type: 'INITIALIZE',
            payload: {
                apiKey: this.options.apiKey,
                modelName: this.options.modelName,
                systemPrompt: this.options.systemPrompt,
                mcpTools: this.options.mcpTools,
                useVertexAI: this.options.useVertexAI,
                vertexProject: this.options.vertexProject,
                vertexLocation: this.options.vertexLocation,
                avatarMode: this.options.avatarMode,
                google1PAvatarName: this.options.google1PAvatarName,
                google1PVoiceName: this.options.google1PVoiceName,
                tools
            }
        });

    } catch (e) {
        console.error('[GeminiLiveApi] Failed to initialize WebWorker:', e);
        this.options.onStateChange('error');
    }
  }

  public disconnect() {
    if (this.worker) {
        this.worker.postMessage({ type: 'DISCONNECT' });
        this.worker.terminate();
        this.worker = null;
    }
  }

  public sendAudioChunk(data: ArrayBuffer) {
    if (this.worker) {
        this.worker.postMessage({ type: 'SEND_AUDIO', payload: data }, [data]);
    }
  }

  public sendVideoFrame(base64Image: string, mimeType: string = 'image/jpeg') {
    if (this.worker) {
        this.worker.postMessage({
            type: 'SEND_VIDEO',
            payload: { data: base64Image, mimeType }
        });
    }
  }

  public sendToolResponse(toolName: string, id: string, result: unknown) {
    if (this.worker) {
        this.worker.postMessage({
            type: 'TOOL_RESPONSE',
            payload: { toolName, id, result }
        });
    }
  }

  public sendTextMessage(text: string) {
    if (this.worker) {
        this.worker.postMessage({ type: 'SEND_TEXT', payload: text });
    }
  }
}

