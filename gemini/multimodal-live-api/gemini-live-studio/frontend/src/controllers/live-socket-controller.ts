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

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import {
  parseToolCallEntry,
  type TranscriptEntry,
} from '../components/session/session-transcript-panel';
import type { AvatarConfigEvent, LiveConfigEvent } from '../domain/presets';
import { showToast } from '../theme/events';

export interface LiveSocketConnectOptions {
  endpoint: '/ws' | '/ws/live';
  config: AvatarConfigEvent | LiveConfigEvent;
  onBinaryFrame: (data: ArrayBuffer) => void;
  onMediaConfig: (msg: Record<string, unknown>) => void;
  onInterrupted: () => void;
  onBeforeTerminate?: () => void;
}

/**
 * Shared ReactiveController (`LiveSocketController`) managing the `/ws` and
 * `/ws/live` WebSocket switchboard lifecycle, transcript merging, tool card
 * updates, interruption handling, graceful 15s termination fallback timer,
 * and user-visible error toasts on abnormal close codes.
 */
export class LiveSocketController implements ReactiveController {
  status = 'Connecting...';
  transcript: TranscriptEntry[] = [];
  isTerminating = false;
  sessionModel = '';
  sessionLocation = '';

  private readonly host: ReactiveControllerHost & EventTarget;
  private ws: WebSocket | null = null;
  private options: LiveSocketConnectOptions | null = null;
  private terminateTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private hasDispatchedDisconnect = false;
  private limitReached = false;
  private hadErrorEvent = false;

  constructor(host: ReactiveControllerHost & EventTarget) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.cleanup();
  }

  connect(options: LiveSocketConnectOptions): void {
    this.cleanup();
    this.options = options;
    this.status = 'Connecting...';
    this.transcript = [];
    this.isTerminating = false;
    this.sessionModel = '';
    this.sessionLocation = '';
    this.hasDispatchedDisconnect = false;
    this.limitReached = false;
    this.hadErrorEvent = false;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${wsProtocol}//${window.location.host}${options.endpoint}`,
    );
    ws.binaryType = 'arraybuffer';
    this.ws = ws;

    ws.onopen = () => {
      if (this.ws !== ws) return;
      this.status = 'Connected';
      this.host.requestUpdate();
      ws.send(JSON.stringify(options.config));
    };

    ws.onmessage = (event) => {
      if (this.ws !== ws) return;
      if (event.data instanceof ArrayBuffer) {
        options.onBinaryFrame(event.data);
        return;
      }
      try {
        const msg = JSON.parse(event.data) as Record<string, unknown>;
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
      this.host.requestUpdate();
    };

    ws.onclose = (event: CloseEvent) => {
      if (this.ws !== ws) return;
      this.status = 'Disconnected';
      this.surfaceCloseToast(event);
      this.cleanup();
      this.dispatchDisconnect();
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

  sendText(rawText: string): void {
    const text = rawText.trim();
    if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.sendPayload({ type: 'text', data: text });
    this.transcript = [...this.transcript, { type: 'user', text }];
    this.host.requestUpdate();
  }

  terminate(): void {
    if (this.isTerminating) return;
    this.isTerminating = true;
    this.status = 'Disconnecting...';
    this.host.requestUpdate();

    this.options?.onBeforeTerminate?.();

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'control', action: 'terminate' }));
      this.terminateTimeoutId = setTimeout(() => {
        this.terminateTimeoutId = null;
        this.cleanup();
        this.dispatchDisconnect();
      }, 15000);
    } else {
      this.cleanup();
      this.dispatchDisconnect();
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

  private handleJsonMessage(msg: Record<string, unknown>): void {
    const type = msg.type;
    if (type === 'session_info') {
      if (typeof msg.model === 'string' && msg.model) {
        this.sessionModel = msg.model;
      }
      if (typeof msg.location === 'string' && msg.location) {
        this.sessionLocation = msg.location;
      }
      this.host.requestUpdate();
    } else if (type === 'media_config') {
      this.options?.onMediaConfig(msg);
    } else if (type === 'transcript' || type === 'output_transcript') {
      const isFinished =
        msg.finished === true ||
        msg.finished === 'true' ||
        type === 'transcript';
      const text = typeof msg.text === 'string' ? msg.text : '';
      this.appendTranscriptTurn('assistant', text, isFinished, true);
    } else if (type === 'input_transcript') {
      const isFinished = msg.finished === true || msg.finished === 'true';
      const text = typeof msg.text === 'string' ? msg.text : '';
      this.appendTranscriptTurn('user', text, isFinished, false);
    } else if (type === 'tool_call') {
      this.transcript = [...this.transcript, parseToolCallEntry(msg)];
      this.host.requestUpdate();
    } else if (type === 'tool_call_cancellation' && Array.isArray(msg.ids)) {
      const cancelledIds = new Set<string>(
        msg.ids.filter((id): id is string => typeof id === 'string'),
      );
      this.transcript = this.transcript.map((entry) =>
        entry.type === 'tool' &&
        entry.toolCard?.id &&
        cancelledIds.has(entry.toolCard.id)
          ? {
              ...entry,
              toolCard: { ...entry.toolCard, cancelled: true },
            }
          : entry,
      );
      this.host.requestUpdate();
    } else if (type === 'interrupted') {
      this.options?.onInterrupted();
      if (this.transcript.length > 0) {
        const last = this.transcript[this.transcript.length - 1];
        if (last.type === 'assistant' && last.isPartial) {
          const next = [...this.transcript];
          next[next.length - 1] = {
            type: 'assistant',
            text: last.text + ' \u2014',
            isPartial: false,
          };
          this.transcript = next;
          this.host.requestUpdate();
        }
      }
    } else if (type === 'status' && msg.error === 'session_limit_reached') {
      this.limitReached = true;
      this.status = '10m Session Limit Reached';
      showToast('10-minute session limit reached.', 'danger');
      this.host.requestUpdate();
    }
  }

  private appendTranscriptTurn(
    role: 'user' | 'assistant',
    text: string,
    isFinished: boolean,
    concatenatePartials: boolean,
  ): void {
    const lastIdx = this.transcript.length - 1;
    if (
      lastIdx >= 0 &&
      this.transcript[lastIdx].type === role &&
      this.transcript[lastIdx].isPartial
    ) {
      const next = [...this.transcript];
      next[lastIdx] = {
        type: role,
        text: concatenatePartials ? next[lastIdx].text + text : text,
        isPartial: !isFinished,
      };
      this.transcript = next;
    } else {
      this.transcript = [
        ...this.transcript,
        { type: role, text, isPartial: !isFinished },
      ];
    }
    this.host.requestUpdate();
  }

  private surfaceCloseToast(event: CloseEvent): void {
    const reason = event.reason?.trim() || '';
    if (this.limitReached || reason === 'Session limit reached') {
      if (!this.limitReached) {
        showToast('10-minute session limit reached.', 'danger');
      }
      return;
    }
    if (event.code === 1007) {
      showToast(reason || 'Invalid session configuration.', 'danger');
      return;
    }
    if (event.code === 1009) {
      showToast(
        reason || 'Message too large \u2014 session disconnected.',
        'danger',
      );
      return;
    }
    if (!this.isTerminating && (event.code !== 1000 || this.hadErrorEvent)) {
      showToast(
        reason
          ? `Session closed: ${reason}`
          : 'Connection to Gemini Live failed or was lost.',
        'danger',
      );
    }
  }

  private dispatchDisconnect(): void {
    if (this.hasDispatchedDisconnect) return;
    this.hasDispatchedDisconnect = true;
    this.host.dispatchEvent(
      new CustomEvent('disconnect', { bubbles: true, composed: true }),
    );
  }
}
