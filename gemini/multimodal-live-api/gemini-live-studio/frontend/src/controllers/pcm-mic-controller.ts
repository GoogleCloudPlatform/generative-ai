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
import { PcmMic } from '../lib/live/pcm-mic';
import { showToast } from '../theme/events';

/**
 * ReactiveController adapter around headless `PcmMic` (`lib/live/pcm-mic.ts`).
 */
export class PcmMicController implements ReactiveController {
  private readonly host: ReactiveControllerHost;
  private readonly mic: PcmMic;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    this.mic = new PcmMic({
      onStateChange: () => this.host.requestUpdate(),
      onError: (err) => {
        console.error('Microphone access denied:', err);
        showToast(
          'Microphone access denied or unavailable. Check browser permissions.',
          'danger',
        );
      },
    });
    host.addController(this);
  }

  get isRecording(): boolean {
    return this.mic.isRecording;
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.stop();
  }

  async toggle(onBase64PcmChunk: (base64: string) => void): Promise<void> {
    await this.mic.toggle(onBase64PcmChunk);
  }

  async start(onBase64PcmChunk: (base64: string) => void): Promise<void> {
    await this.mic.start(onBase64PcmChunk);
  }

  stop(): void {
    this.mic.stop();
  }
}
