// PlaybackProcessor handles continuous circular audio buffer playback on the audio thread.

interface AudioWorkletProcessor {
  readonly port: MessagePort;
  process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean;
}

declare let AudioWorkletProcessor: {
  prototype: AudioWorkletProcessor;
  new(): AudioWorkletProcessor;
};

declare function registerProcessor(name: string, processorCtor: (new (options?: unknown) => AudioWorkletProcessor)): void;

class PlaybackProcessor extends AudioWorkletProcessor {
  private buffer: Float32Array;
  private writeIndex = 0;
  private readIndex = 0;
  private isPlaying = false;
  private bufferLength: number;

  constructor() {
    super();
    // Pre-allocate 15 seconds of 24kHz audio
    this.bufferLength = 24000 * 15;
    this.buffer = new Float32Array(this.bufferLength);

    this.port.onmessage = (event) => {
      if (event.data.type === 'FLUSH') {
        this.writeIndex = 0;
        this.readIndex = 0;
        this.isPlaying = false;
        this.buffer.fill(0);
      } else if (event.data.type === 'AUDIO') {
        const floatData = new Float32Array(event.data.payload);
        
        for (let i = 0; i < floatData.length; i++) {
            this.buffer[this.writeIndex] = floatData[i];
            this.writeIndex = (this.writeIndex + 1) % this.bufferLength;
        }
        
        this.isPlaying = true;
      }
    };
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const output = outputs[0];
    const channel = output[0];
    
    if (!this.isPlaying || this.readIndex === this.writeIndex) {
      for (let i = 0; i < channel.length; i++) {
        channel[i] = 0;
      }
      if (this.readIndex === this.writeIndex && this.isPlaying) {
        this.isPlaying = false;
      }
      return true;
    }

    for (let i = 0; i < channel.length; i++) {
      if (this.readIndex !== this.writeIndex) {
        channel[i] = this.buffer[this.readIndex];
        this.readIndex = (this.readIndex + 1) % this.bufferLength;
      } else {
        channel[i] = 0;
      }
    }

    return true;
  }
}

registerProcessor('playback-processor', PlaybackProcessor);
export {};
