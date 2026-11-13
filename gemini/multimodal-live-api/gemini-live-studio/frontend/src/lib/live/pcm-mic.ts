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

/**
 * Creates a 16 kHz AudioContext with an inline AudioWorklet processor that
 * accumulates Float32 microphone samples into 2048-sample Int16 chunks
 * (~128 ms at 16 kHz) off the main UI thread.
 */
export async function createPcmCaptureContext(): Promise<AudioContext> {
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const workletUrl = URL.createObjectURL(
    new Blob(
      [
        `
      class PcmProcessor extends AudioWorkletProcessor {
        constructor() {
          super();
          this.bufferSize = 2048;
          this.buffer = new Int16Array(this.bufferSize);
          this.offset = 0;
        }

        process(inputs) {
          const input = inputs[0];
          if (input && input.length > 0) {
            const channel = input[0];
            for (let i = 0; i < channel.length; i++) {
              const s = Math.max(-1, Math.min(1, channel[i]));
              this.buffer[this.offset] = s < 0 ? s * 0x8000 : s * 0x7FFF;
              this.offset++;

              if (this.offset >= this.bufferSize) {
                this.port.postMessage(this.buffer);
                this.offset = 0;
              }
            }
          }
          return true;
        }
      }
      registerProcessor('pcm-processor', PcmProcessor);
    `,
      ],
      { type: 'application/javascript' },
    ),
  );
  try {
    await audioContext.audioWorklet.addModule(workletUrl);
  } catch (err) {
    audioContext.close().catch(() => {});
    throw err;
  } finally {
    URL.revokeObjectURL(workletUrl);
  }
  return audioContext;
}

/**
 * Converts an Int16Array chunk into little-endian PCM bytes.
 */
export function int16ArrayToLittleEndianBytes(int16: Int16Array): Uint8Array {
  const buffer = new ArrayBuffer(int16.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < int16.length; i++) {
    view.setInt16(i * 2, int16[i], true);
  }
  return new Uint8Array(buffer);
}

/**
 * Encodes a Uint8Array into a standard Base64 string.
 */
export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Computes normalized RMS energy in [0, 1] for an Int16 PCM frame.
 */
export function computeInt16Rms(int16: Int16Array): number {
  if (int16.length === 0) return 0;
  let sumSq = 0;
  for (let i = 0; i < int16.length; i++) {
    const norm = int16[i] / 32768;
    sumSq += norm * norm;
  }
  return Math.min(1, Math.sqrt(sumSq / int16.length));
}

export interface PcmMicCallbacks {
  onStateChange?: (recording: boolean) => void;
  onError?: (err: unknown) => void;
  onRmsLevel?: (rms: number) => void;
}

/**
 * Framework-agnostic 16 kHz AudioWorklet microphone capture with an async
 * startToken guard so rapid start/stop transitions never leak tracks.
 */
export class PcmMic {
  isRecording = false;
  isSoftMuted = false;

  private readonly callbacks: PcmMicCallbacks;
  private audioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private startToken = 0;

  constructor(callbacks: PcmMicCallbacks = {}) {
    this.callbacks = callbacks;
  }

  /**
   * Soft-mutes outbound PCM chunks without releasing the hardware microphone
   * stream (used when gating mic input during assistant speech).
   */
  setSoftMuted(muted: boolean): void {
    this.isSoftMuted = muted;
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
        if (this.isSoftMuted) {
          this.callbacks.onRmsLevel?.(0);
          return;
        }
        const int16Data = e.data as Int16Array;
        this.callbacks.onRmsLevel?.(computeInt16Rms(int16Data));
        const uint8Data = int16ArrayToLittleEndianBytes(int16Data);
        const base64Data = uint8ArrayToBase64(uint8Data);
        onBase64PcmChunk(base64Data);
      };

      source.connect(this.audioWorkletNode);
      this.isRecording = true;
      this.callbacks.onStateChange?.(true);
    } catch (err) {
      this.stop();
      this.callbacks.onError?.(err);
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
      this.callbacks.onStateChange?.(false);
    }
  }
}
