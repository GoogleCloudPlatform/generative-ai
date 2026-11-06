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
import { Fmp4Player } from '../lib/live/fmp4-player';

/**
 * ReactiveController adapter around headless `Fmp4Player` (`lib/live/fmp4-player.ts`).
 */
export class Fmp4PlayerController implements ReactiveController {
  private readonly host: ReactiveControllerHost;
  private readonly player: Fmp4Player;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    this.player = new Fmp4Player({
      onFirstChunk: () => this.host.requestUpdate(),
    });
    host.addController(this);
  }

  get hasReceivedVideo(): boolean {
    return this.player.hasReceivedVideo;
  }

  get configuredCodec(): string {
    return this.player.configuredCodec;
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.destroy();
  }

  attach(videoEl: HTMLVideoElement): void {
    this.player.attach(videoEl);
  }

  setCodec(codecs: string): void {
    this.player.setCodec(codecs);
  }

  appendChunk(chunk: Uint8Array): void {
    this.player.appendChunk(chunk);
  }

  flushAndAbort(): void {
    this.player.flushAndAbort();
  }

  destroy(): void {
    this.player.destroy();
  }
}
