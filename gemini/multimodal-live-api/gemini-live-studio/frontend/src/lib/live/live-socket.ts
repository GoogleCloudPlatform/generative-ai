// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import {
  TranscriptAssembler,
  type TranscriptItem,
} from './transcript-assembler';

export interface CloseDiagnostic {
  kind: 'limit' | 'invalid_config' | 'too_large' | 'abnormal';
  message: string;
}

/**
 * Classifies a WebSocket CloseEvent into a user-facing diagnostic message, or
 * `null` when the close was a normal user-requested termination (1000) or an
 * already-announced 10-minute session cap.
 */
export function describeCloseEvent(
  code: number,
  rawReason: string | undefined,
  state: {
    limitReachedAlreadySurfaced: boolean;
    isTerminating: boolean;
    hadErrorEvent: boolean;
  },
): CloseDiagnostic | null {
  const reason = rawReason?.trim() || '';
  if (state.limitReachedAlreadySurfaced || reason === 'Session limit reached') {
    if (state.limitReachedAlreadySurfaced) {
      return null;
    }
    return { kind: 'limit', message: '10-minute session limit reached.' };
  }
  if (code === 1007) {
    return {
      kind: 'invalid_config',
      message: reason || 'Invalid session configuration.',
    };
  }
  if (code === 1009) {
    return {
      kind: 'too_large',
      message: reason || 'Message too large \u2014 session disconnected.',
    };
  }
  if (!state.isTerminating && (code !== 1000 || state.hadErrorEvent)) {
    return {
      kind: 'abnormal',
      message: reason
        ? `Session closed: ${reason}`
        : 'Connection to Gemini Live failed or was lost.',
    };
  }
  return null;
}

export interface LiveSocketClientOptions {
  url?: string;
  endpoint?: string;
  initialPayload?: unknown;
  terminateTimeoutMs?: number;
  onBinaryFrame?: (data: ArrayBuffer) => void;
  onMediaConfig?: (msg: Record<string, unknown>) => void;
  onInterrupted?: () => void;
  onTurnComplete?: () => void;
  onBeforeTerminate?: () => void;
  onProactiveAlert?: (msg: Record<string, unknown>) => void;
  onCustomMessage?: (msg: Record<string, unknown>) => void;
  onStateChange?: () => void;
  onWarning?: (message: string) => void;
  onDisconnected?: () => void;
}

/**
 * Framework-agnostic WebSocket switchboard client handling initial setup,
 * binary media routing, partial/final transcript assembly, tool call cards and
 * cancellations, graceful farewell termination, and RFC 6455 close diagnostics.
 */
export class LiveSocketClient {
  status = 'Connecting...';
  isTerminating = false;
  sessionModel = '';
  sessionLocation = '';

  readonly transcriptAssembler = new TranscriptAssembler();

  private ws: WebSocket | null = null;
  private options: LiveSocketClientOptions | null = null;
  private terminateTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private hasNotifiedDisconnect = false;
  private limitReached = false;
  private hadErrorEvent = false;

  get transcript(): TranscriptItem[] {
    return this.transcriptAssembler.entries;
  }

  connect(options: LiveSocketClientOptions): void {
    this.cleanup();
    this.options = options;
    this.status = 'Connecting...';
    this.transcriptAssembler.reset();
    this.isTerminating = false;
    this.sessionModel = '';
    this.sessionLocation = '';
    this.hasNotifiedDisconnect = false;
    this.limitReached = false;
    this.hadErrorEvent = false;

    const wsUrl = options.url ?? this.resolveEndpointUrl(options.endpoint);
    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      if (this.ws !== ws) return;
      this.status = 'Connected';
      this.options?.onStateChange?.();
      if (options.initialPayload !== undefined) {
        ws.send(JSON.stringify(options.initialPayload));
      }
    };

    ws.onmessage = (event) => {
      if (this.ws !== ws) return;
      if (event.data instanceof ArrayBuffer) {
        options.onBinaryFrame?.(event.data);
        return;
      }
      try {
        const msg = JSON.parse(event.data as string) as Record<string, unknown>;
        this.handleJsonMessage(msg);
      } catch (e) {
        console.error('Error parsing WebSocket message JSON', e);
      }
    };

    ws.onerror = (err) => {
      if (this.ws !== ws) return;
      console.error('WebSocket Error:', err);
      this.hadErrorEvent = true;
      this.status = 'Error connecting';
      this.options?.onStateChange?.();
    };

    ws.onclose = (event: CloseEvent) => {
      if (this.ws !== ws) return;
      this.status = 'Disconnected';
      const diag = describeCloseEvent(event.code, event.reason, {
        limitReachedAlreadySurfaced: this.limitReached,
        isTerminating: this.isTerminating,
        hadErrorEvent: this.hadErrorEvent,
      });
      if (diag) {
        this.options?.onWarning?.(diag.message);
      }
      this.cleanup();
      this.notifyDisconnect();
    };
  }

  sendPayload(payload: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  sendAudioChunk(base64Data: string): void {
    this.sendPayload({
      type: 'audio',
      mimeType: 'audio/pcm;rate=16000',
      data: base64Data,
    });
  }

  sendVideoFrame(base64Jpeg: string): void {
    this.sendPayload({
      type: 'video',
      mimeType: 'image/jpeg',
      data: base64Jpeg,
    });
  }

  sendText(rawText: string): boolean {
    const text = rawText.trim();
    if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.sendPayload({ type: 'text', data: text });
    this.transcriptAssembler.addUserText(text);
    this.options?.onStateChange?.();
    return true;
  }

  sendToolResult(
    id: string,
    name: string,
    result: Record<string, unknown>,
    options?: { imageDataUrl?: string; execMs?: number },
  ): void {
    this.sendPayload({
      type: 'tool_result',
      id,
      name,
      result,
      ...(options?.imageDataUrl ? { image: options.imageDataUrl } : {}),
      ...(options?.execMs !== undefined ? { execMs: options.execMs } : {}),
    });
  }

  terminate(): void {
    if (this.isTerminating) return;
    this.isTerminating = true;
    this.status = 'Disconnecting...';
    this.options?.onStateChange?.();

    this.options?.onBeforeTerminate?.();

    const timeoutMs = this.options?.terminateTimeoutMs ?? 15000;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'control', action: 'terminate' }));
      this.terminateTimeoutId = setTimeout(() => {
        this.terminateTimeoutId = null;
        this.cleanup();
        this.notifyDisconnect();
      }, timeoutMs);
    } else {
      this.cleanup();
      this.notifyDisconnect();
    }
  }

  cleanup(): void {
    if (this.terminateTimeoutId !== null) {
      clearTimeout(this.terminateTimeoutId);
      this.terminateTimeoutId = null;
    }
    this.options?.onBeforeTerminate?.();
    if (this.ws) {
      const ws = this.ws;
      this.ws = null;
      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        ws.close();
      }
    }
  }

  private resolveEndpointUrl(endpoint = '/ws'): string {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}${endpoint}`;
  }

  private handleJsonMessage(msg: Record<string, unknown>): void {
    const type = msg.type;
    if (type === 'session_info') {
      if (typeof msg.model === 'string' && msg.model) {
        this.sessionModel = msg.model;
      }
      if (typeof msg.location === 'string' && msg.location) {
        this.sessionLocation = msg.location;
      }
      this.options?.onStateChange?.();
    } else if (type === 'media_config') {
      this.options?.onMediaConfig?.(msg);
    } else if (type === 'transcript' || type === 'output_transcript') {
      const isFinished =
        msg.finished === true ||
        msg.finished === 'true' ||
        type === 'transcript';
      const text = typeof msg.text === 'string' ? msg.text : '';
      this.transcriptAssembler.appendTurn('assistant', text, isFinished, true);
      this.options?.onStateChange?.();
    } else if (type === 'input_transcript') {
      const isFinished = msg.finished === true || msg.finished === 'true';
      const text = typeof msg.text === 'string' ? msg.text : '';
      this.transcriptAssembler.appendTurn('user', text, isFinished, false);
      this.options?.onStateChange?.();
    } else if (type === 'tool_call') {
      this.transcriptAssembler.addToolCall(msg);
      this.options?.onStateChange?.();
    } else if (type === 'tool_call_cancellation' && Array.isArray(msg.ids)) {
      const ids = msg.ids.filter((id): id is string => typeof id === 'string');
      this.transcriptAssembler.cancelToolCalls(ids);
      this.options?.onStateChange?.();
    } else if (type === 'interrupted') {
      this.options?.onInterrupted?.();
      if (this.transcriptAssembler.markInterrupted()) {
        this.options?.onStateChange?.();
      }
    } else if (type === 'turn_complete') {
      if (this.transcriptAssembler.sealActiveTurns()) {
        this.options?.onStateChange?.();
      }
      this.options?.onTurnComplete?.();
    } else if (type === 'proactive_alert') {
      this.options?.onProactiveAlert?.(msg);
    } else if (
      type === 'status' &&
      (msg.error === 'session_limit_reached' ||
        msg.message === 'session_limit_reached')
    ) {
      this.limitReached = true;
      this.status = '10m Session Limit Reached';
      this.options?.onWarning?.('10-minute session limit reached.');
      this.options?.onStateChange?.();
    } else {
      this.options?.onCustomMessage?.(msg);
    }
  }

  private notifyDisconnect(): void {
    if (this.hasNotifiedDisconnect) return;
    this.hasNotifiedDisconnect = true;
    this.options?.onDisconnected?.();
  }
}
