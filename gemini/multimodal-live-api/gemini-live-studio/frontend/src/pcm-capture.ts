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
 * Shared 16kHz PCM microphone capture pipeline using AudioWorkletNode.
 * Buffers Float32 samples into 2048-sample Int16 chunks (~128ms at 16kHz)
 * and posts each full chunk to the main thread via port.onmessage.
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
          this.bufferSize = 2048; // Send chunks roughly every 128ms at 16kHz
          this.buffer = new Int16Array(this.bufferSize);
          this.offset = 0;
        }

        process(inputs, outputs, parameters) {
          const input = inputs[0];
          if (input && input.length > 0) {
            const channel = input[0];
            for (let i = 0; i < channel.length; i++) {
              // Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
              let s = Math.max(-1, Math.min(1, channel[i]));
              this.buffer[this.offset] = s < 0 ? s * 0x8000 : s * 0x7FFF;
              this.offset++;

              if (this.offset >= this.bufferSize) {
                // Post the buffer to the main thread
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
 * Converts a chunk posted by the 'pcm-processor' worklet (an Int16Array)
 * into little-endian bytes.
 */
export function int16ArrayToLittleEndianBytes(int16: Int16Array): Uint8Array {
  const buffer = new ArrayBuffer(int16.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < int16.length; i++) {
    view.setInt16(i * 2, int16[i], true); // true for little-endian
  }
  return new Uint8Array(buffer);
}

/**
 * Converts a Uint8Array into a Base64 string safely.
 */
export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
