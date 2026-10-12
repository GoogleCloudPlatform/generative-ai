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
  createPcmCaptureContext,
  int16ArrayToLittleEndianBytes,
  uint8ArrayToBase64,
} from '../pcm-capture';
import { showToast } from '../theme/events';

/**
 * ReactiveController managing 16kHz PCM microphone capture via AudioWorkletNode.
 * Automatically releases microphone tracks and AudioContext on disconnect.
 */
export class PcmMicController implements ReactiveController {
  isRecording = false;

  private readonly host: ReactiveControllerHost;
  private audioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private startToken = 0;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.stop();
  }

  async toggle(onBase64PcmChunk: (base64: string) => void): Promise<void> {
    if (this.isRecording) {
      this.stop();
    } else {
      await this.start(onBase64PcmChunk);
    }
  }

  async start(onBase64PcmChunk: (base64: string) => void): Promise<void> {
    const token = ++this.startToken;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000 },
      });
      if (token !== this.startToken) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((t) => t.stop());
      }
      this.mediaStream = stream;

      if (!this.audioContext) {
        const ctx = await createPcmCaptureContext();
        if (token !== this.startToken) {
          ctx.close().catch(() => {});
          this.stop();
          return;
        }
        this.audioContext = ctx;
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
        if (token !== this.startToken || !this.audioContext) {
          this.stop();
          return;
        }
      }

      const source = this.audioContext.createMediaStreamSource(
        this.mediaStream,
      );
      this.audioWorkletNode = new AudioWorkletNode(
        this.audioContext,
        'pcm-processor',
      );

      this.audioWorkletNode.port.onmessage = (e) => {
        const int16Data = e.data as Int16Array;
        const uint8Data = int16ArrayToLittleEndianBytes(int16Data);
        const base64Data = uint8ArrayToBase64(uint8Data);
        onBase64PcmChunk(base64Data);
      };

      source.connect(this.audioWorkletNode);
      this.isRecording = true;
      this.host.requestUpdate();
    } catch (err) {
      console.error('Microphone access denied:', err);
      this.stop();
      showToast(
        'Microphone access denied or unavailable. Check browser permissions.',
        'danger',
      );
    }
  }

  stop(): void {
    this.startToken++;
    if (this.audioWorkletNode) {
      this.audioWorkletNode.port.onmessage = null;
      this.audioWorkletNode.disconnect();
      this.audioWorkletNode = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.isRecording) {
      this.isRecording = false;
      this.host.requestUpdate();
    }
  }
}
