/**
 * Audio Worklet Processor for capturing and processing audio
 */

class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];

    if (input && input.length > 0) {
      const inputChannel = input[0];

      // Buffer the incoming audio
      for (let i = 0; i < inputChannel.length; i++) {
        this.buffer[this.bufferIndex++] = inputChannel[i];
        // When buffer is full, send it to main thread
        if (this.bufferIndex >= this.bufferSize) {
          // Send the buffered audio to the main thread
          this.port.postMessage({
            type: "audio",
            data: this.buffer.slice(),
          });

          // Reset buffer
          this.bufferIndex = 0;
        }
      }
    }

    // Return true to keep the processor alive
    return true;
  }
}

// Register the processor
registerProcessor("audio-capture-processor", AudioCaptureProcessor);
