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
import type { TranscriptEntry } from '../components/session/session-transcript-panel';
import type { AvatarConfigEvent, LiveConfigEvent } from '../domain/presets';
import { LiveSocketClient } from '../lib/live/live-socket';
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
 * ReactiveController adapter around headless `LiveSocketClient`
 * (`lib/live/live-socket.ts`), bridging Lit updates, toast notifications, and
 * `disconnect` CustomEvents.
 */
export class LiveSocketController implements ReactiveController {
  private readonly host: ReactiveControllerHost & EventTarget;
  private readonly client = new LiveSocketClient();

  constructor(host: ReactiveControllerHost & EventTarget) {
    this.host = host;
    host.addController(this);
  }

  get status(): string {
    return this.client.status;
  }

  get transcript(): TranscriptEntry[] {
    return this.client.transcript;
  }

  get isTerminating(): boolean {
    return this.client.isTerminating;
  }

  get sessionModel(): string {
    return this.client.sessionModel;
  }

  get sessionLocation(): string {
    return this.client.sessionLocation;
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.cleanup();
  }

  connect(options: LiveSocketConnectOptions): void {
    this.client.connect({
      endpoint: options.endpoint,
      initialPayload: options.config,
      onBinaryFrame: options.onBinaryFrame,
      onMediaConfig: options.onMediaConfig,
      onInterrupted: options.onInterrupted,
      onBeforeTerminate: options.onBeforeTerminate,
      onStateChange: () => this.host.requestUpdate(),
      onWarning: (msg) => showToast(msg, 'danger'),
      onDisconnected: () => {
        this.host.dispatchEvent(
          new CustomEvent('disconnect', { bubbles: true, composed: true }),
        );
      },
    });
  }

  sendPayload(payload: Record<string, unknown>): void {
    this.client.sendPayload(payload);
  }

  sendAudioChunk(base64Data: string): void {
    this.client.sendAudioChunk(base64Data);
  }

  sendVideoFrame(base64Jpeg: string): void {
    this.client.sendVideoFrame(base64Jpeg);
  }

  sendText(rawText: string): void {
    this.client.sendText(rawText);
  }

  terminate(): void {
    this.client.terminate();
  }

  cleanup(): void {
    this.client.cleanup();
  }
}
