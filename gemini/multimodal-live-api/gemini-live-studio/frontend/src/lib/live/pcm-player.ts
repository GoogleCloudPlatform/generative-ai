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

export interface PcmPlayerCallbacks {
  onStateChange?: () => void;
  onPlayingChange?: (playing: boolean) => void;
}

/**
 * Framework-agnostic gapless 24 kHz PCM audio player with barge-in flushing and
 * Audio-Reactive Mute routing:
 *   BufferSource -> AnalyserNode -> OutputGainNode -> AudioContext.destination
 *
 * Setting `isMuted` zeroes `OutputGainNode.gain` so frequency visualizers keep
 * animating during model speech even when speaker audio is muted.
 */
export class PcmPlayer {
  hasReceivedAudio = false;
  isMuted = false;
  sampleRate = 24000;

  private readonly callbacks: PcmPlayerCallbacks;
  private audioContext: AudioContext | null = null;
  private analyserNode: AnalyserNode | null = null;
  private outputGainNode: GainNode | null = null;
  private audioQueue: AudioBuffer[] = [];
  private activeSources = new Set<AudioBufferSourceNode>();
  private nextPlayTime = 0;

  constructor(callbacks: PcmPlayerCallbacks = {}) {
    this.callbacks = callbacks;
  }

  get analyser(): AnalyserNode | null {
    return this.analyserNode;
  }

  get context(): AudioContext | null {
    return this.audioContext;
  }

  get isPlaying(): boolean {
    return this.activeSources.size > 0;
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
    this.callbacks.onStateChange?.();
  }

  toggleMute(): void {
    this.setMuted(!this.isMuted);
  }

  setMuted(muted: boolean): void {
    if (this.isMuted === muted) return;
    this.isMuted = muted;
    if (this.outputGainNode) {
      this.outputGainNode.gain.value = this.isMuted ? 0 : 1;
    }
    this.callbacks.onStateChange?.();
  }

  /**
   * Advances the scheduled playhead by `seconds` so procedural chimes do not
   * overlap incoming speech chunks.
   */
  deferPlayback(seconds: number): void {
    if (!this.audioContext || seconds <= 0) return;
    const target = this.audioContext.currentTime + seconds;
    if (this.nextPlayTime < target) {
      this.nextPlayTime = target;
    }
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
      this.callbacks.onStateChange?.();
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
    const wasPlaying = this.activeSources.size > 0;
    this.audioQueue = [];
    for (const source of this.activeSources) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Ignore already-stopped nodes.
      }
    }
    this.activeSources.clear();
    this.nextPlayTime = 0;
    if (wasPlaying) {
      this.callbacks.onPlayingChange?.(false);
    }
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

    const wasEmpty = this.activeSources.size === 0;
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
        if (this.activeSources.size === 0) {
          this.callbacks.onPlayingChange?.(false);
        }
      };
      this.activeSources.add(source);
      source.start(this.nextPlayTime);
      this.nextPlayTime += buffer.duration;
    }

    if (wasEmpty && this.activeSources.size > 0) {
      this.callbacks.onPlayingChange?.(true);
    }
  }
}
