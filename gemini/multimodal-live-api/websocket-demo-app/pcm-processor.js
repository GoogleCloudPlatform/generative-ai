class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffer = new Float32Array();

        // Correct way to handle messages in AudioWorklet
        this.port.onmessage = (e) => {
            const newData = e.data;
            const newBuffer = new Float32Array(this.buffer.length + newData.length);
            newBuffer.set(this.buffer);
            newBuffer.set(newData, this.buffer.length);
            this.buffer = newBuffer;
        };
    }

    process(inputs, outputs, parameters) {
        const output = outputs[0];
        const channelData = output[0];

        if (this.buffer.length >= channelData.length) {
            channelData.set(this.buffer.slice(0, channelData.length));
            this.buffer = this.buffer.slice(channelData.length);
            return true;
        }

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);