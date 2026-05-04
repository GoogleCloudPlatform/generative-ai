# PCM Audio Debugger

A single-file HTML tool for debugging and testing PCM audio data. It combines an audio recorder (to generate Base64 PCM) and a packet player (to decode and play Base64 PCM).

## Features

- **Zero Dependencies**: Just open the HTML file in any modern browser.
- **PCM Generator**: Record microphone input and convert it to Base64-encoded PCM.
  - Supports various sample rates (8kHz - 48kHz).
  - Supports Mono/Stereo.
  - Supports 8-bit, 16-bit (signed), and 32-bit (float) formats.
- **Packet Player**: Decode and play back Base64 PCM strings.
  - Paste multiple sequential packets to test streaming audio flows.
  - Handles different PCM formats and sample rates.

## Usage

1.  Open `pcm-audio-debugger.html` in your web browser.

### To Generate PCM Data

1.  Switch to the **PCM Generator** tab.
2.  Select your microphone.
3.  Configure the target Sample Rate, Channels, and Bit Depth.
4.  Press **Record**, speak, and then **Stop**.
5.  Copy the generated Base64 string.

### To Play PCM Data

1.  Switch to the **Packet Player** tab.
2.  Paste your Base64 PCM string into the text area.
3.  (Optional) Click **Add Packet** to add more segments.
4.  Ensure the settings (Sample Rate, etc.) match your data.
5.  Click **Decode & Play All Packets**.
