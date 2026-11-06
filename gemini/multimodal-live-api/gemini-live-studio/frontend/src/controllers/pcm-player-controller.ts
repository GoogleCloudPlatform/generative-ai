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
import { PcmPlayer } from '../lib/live/pcm-player';

/**
 * ReactiveController adapter around headless `PcmPlayer` (`lib/live/pcm-player.ts`).
 */
export class PcmPlayerController implements ReactiveController {
  private readonly host: ReactiveControllerHost;
  private readonly player: PcmPlayer;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    this.player = new PcmPlayer({
      onStateChange: () => this.host.requestUpdate(),
    });
    host.addController(this);
  }

  get hasReceivedAudio(): boolean {
    return this.player.hasReceivedAudio;
  }

  get isMuted(): boolean {
    return this.player.isMuted;
  }

  get sampleRate(): number {
    return this.player.sampleRate;
  }

  get analyser(): AnalyserNode | null {
    return this.player.analyser;
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.destroy();
  }

  init(sampleRate = 24000): void {
    this.player.init(sampleRate);
  }

  toggleMute(): void {
    this.player.toggleMute();
  }

  feed(pcmData: ArrayBuffer): void {
    this.player.feed(pcmData);
  }

  flushAndInterrupt(): void {
    this.player.flushAndInterrupt();
  }

  destroy(): void {
    this.player.destroy();
  }
}
