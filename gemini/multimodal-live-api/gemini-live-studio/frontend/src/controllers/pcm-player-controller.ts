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

/**
 * ReactiveController managing gapless 24kHz PCM audio playback, interruption
 * flushing, and audio-reactive frequency analysis (`AnalyserNode`).
 *
 * Audio routing follows the Audio-Reactive Mute pattern:
 *   BufferSource -> AnalyserNode -> OutputGainNode -> AudioContext.destination
 * Muting sets `OutputGainNode.gain.value = 0` so the visualizer remains
 * reactive to model speech even when speaker output is muted.
 */
export class PcmPlayerController implements ReactiveController {
  hasReceivedAudio = false;
  isMuted = false;
  sampleRate = 24000;

  private readonly host: ReactiveControllerHost;
  private audioContext: AudioContext | null = null;
  private analyserNode: AnalyserNode | null = null;
  private outputGainNode: GainNode | null = null;
  private audioQueue: AudioBuffer[] = [];
  private activeSources = new Set<AudioBufferSourceNode>();
  private nextPlayTime = 0;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  get analyser(): AnalyserNode | null {
    return this.analyserNode;
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.destroy();
  }

  init(sampleRate = 24000): void {
    if (this.audioContext && this.sampleRate === sampleRate) {
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume().catch(() => {});
      }
      return;
    }

    this.destroyContext();
    this.sampleRate = sampleRate > 0 ? sampleRate : 24000;

    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    this.audioContext = new AudioCtx({ sampleRate: this.sampleRate });

    this.analyserNode = this.audioContext.createAnalyser();
    this.analyserNode.fftSize = 256;
    this.analyserNode.smoothingTimeConstant = 0.8;

    this.outputGainNode = this.audioContext.createGain();
    this.outputGainNode.gain.value = this.isMuted ? 0 : 1;

    this.analyserNode.connect(this.outputGainNode);
    this.outputGainNode.connect(this.audioContext.destination);
    this.host.requestUpdate();
  }

  toggleMute(): void {
    this.isMuted = !this.isMuted;
    if (this.outputGainNode) {
      this.outputGainNode.gain.value = this.isMuted ? 0 : 1;
    }
    this.host.requestUpdate();
  }

  feed(pcmData: ArrayBuffer): void {
    const evenByteLength = pcmData.byteLength & ~1;
    if (evenByteLength === 0) return;

    if (!this.audioContext) {
      this.init(this.sampleRate);
    }
    if (!this.audioContext || !this.analyserNode) return;

    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume().catch(() => {});
    }

    if (!this.hasReceivedAudio) {
      this.hasReceivedAudio = true;
      this.host.requestUpdate();
    }

    const alignedBuffer =
      evenByteLength === pcmData.byteLength
        ? pcmData
        : pcmData.slice(0, evenByteLength);
    const int16 = new Int16Array(alignedBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }

    const buffer = this.audioContext.createBuffer(
      1,
      float32.length,
      this.sampleRate,
    );
    buffer.getChannelData(0).set(float32);
    this.audioQueue.push(buffer);
    this.schedulePlayback();
  }

  flushAndInterrupt(): void {
    this.audioQueue = [];
    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Ignore already-stopped nodes
      }
    }
    this.activeSources.clear();
    this.nextPlayTime = 0;
  }

  destroy(): void {
    this.destroyContext();
    this.hasReceivedAudio = false;
  }

  private destroyContext(): void {
    this.flushAndInterrupt();
    this.analyserNode = null;
    this.outputGainNode = null;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
    }
    this.audioContext = null;
  }

  private schedulePlayback(): void {
    if (
      !this.audioContext ||
      !this.analyserNode ||
      this.audioQueue.length === 0
    ) {
      return;
    }

    const currentTime = this.audioContext.currentTime;
    if (this.nextPlayTime < currentTime) {
      this.nextPlayTime = currentTime;
    }

    while (this.audioQueue.length > 0) {
      const buffer = this.audioQueue.shift()!;
      const source = this.audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(this.analyserNode);
      source.onended = () => {
        this.activeSources.delete(source);
      };
      this.activeSources.add(source);
      source.start(this.nextPlayTime);
      this.nextPlayTime += buffer.duration;
    }
  }
}
