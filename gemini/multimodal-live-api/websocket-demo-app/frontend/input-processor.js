// input-processor.js

class InputProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    // Get the audio data from the first input channel.
    const input = inputs[0];
    const channelData = input[0];

    // If there's no audio data, do nothing.
    if (!channelData) return true;

    // Convert the 32-bit float audio data to 16-bit PCM.
    const pcm16Data = new Int16Array(channelData.length);
    for (let i = 0; i < channelData.length; i++) {
      // Clamp the values to the -1.0 to 1.0 range.
      const s = Math.max(-1, Math.min(1, channelData[i]));
      // Convert to 16-bit integer.
      pcm16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // Send the processed PCM data back to the main thread.
    this.port.postMessage(pcm16Data);

    // Return true to keep the processor alive.
    return true;
  }
}

registerProcessor('input-processor', InputProcessor);