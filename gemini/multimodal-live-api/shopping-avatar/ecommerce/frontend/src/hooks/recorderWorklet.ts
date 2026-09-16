// RecorderProcessor downsamples client microphone input and runs voice detection.

interface AudioWorkletProcessor {
  readonly port: MessagePort;
  process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean;
}

declare let AudioWorkletProcessor: {
  prototype: AudioWorkletProcessor;
  new(): AudioWorkletProcessor;
};

declare function registerProcessor(name: string, processorCtor: (new (options?: unknown) => AudioWorkletProcessor)): void;
declare const sampleRate: number;

class RecorderProcessor extends AudioWorkletProcessor {
  private bufferSize = 512; // ~32ms at 16kHz
  private buffer = new Float32Array(this.bufferSize);
  private bufferIndex = 0;
  private isMuted = false;

  private silenceFrames = 0;
  private isSpeaking = false;
  private energyThreshold = 0.005; 
  private silenceThresholdFrames = 3; 

  constructor() {
    super();
    this.port.onmessage = (event) => {
      if (event.data.type === 'SET_MUTED') {
        this.isMuted = event.data.payload;
        if (this.isMuted) {
          this.buffer.fill(0);
          this.bufferIndex = 0;
          if (this.isSpeaking) {
            this.isSpeaking = false;
            const exactDelayMs = (this.bufferSize / sampleRate) * 1000 * this.silenceThresholdFrames;
            this.port.postMessage({ type: 'VAD_SILENCE', delayMs: exactDelayMs });
          }
        }
      }
    };
  }

  process(inputs: Float32Array[][]): boolean {
    if (this.isMuted) return true;

    const input = inputs[0];
    if (!input || !input[0]) return true;

    const inputChannel = input[0];
    
    for (let i = 0; i < inputChannel.length; i++) {
      this.buffer[this.bufferIndex++] = inputChannel[i];
      
      if (this.bufferIndex >= this.bufferSize) {
        this.processVAD();
        this.sendBuffer();
        this.bufferIndex = 0;
      }
    }

    return true;
  }

  private processVAD() {
    let sumSquares = 0;
    for (let i = 0; i < this.bufferSize; i++) {
        sumSquares += this.buffer[i] * this.buffer[i];
    }
    const rms = Math.sqrt(sumSquares / this.bufferSize);

    if (rms > this.energyThreshold) {
        if (!this.isSpeaking) {
            this.isSpeaking = true;
            this.port.postMessage({ type: 'VAD_START' });
        }
        this.silenceFrames = 0;
    } else {
        if (this.isSpeaking) {
            this.silenceFrames++;
            if (this.silenceFrames >= this.silenceThresholdFrames) {
                this.isSpeaking = false;
                const exactDelayMs = (this.bufferSize / sampleRate) * 1000 * this.silenceThresholdFrames;
                this.port.postMessage({ type: 'VAD_SILENCE', delayMs: exactDelayMs });
            }
        }
    }
  }

  private sendBuffer() {
    const pcmData = new Int16Array(this.buffer.length);
    for (let i = 0; i < this.buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, this.buffer[i]));
      pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // Pass transferable buffer array
    this.port.postMessage(pcmData.buffer, [pcmData.buffer]);
  }
}

registerProcessor('recorder-processor', RecorderProcessor);
export {};
