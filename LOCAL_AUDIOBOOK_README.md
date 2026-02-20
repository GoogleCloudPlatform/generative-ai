# Local Audiobook Generator for Apple Silicon

Generate audiobooks using local LLMs running natively on Apple Silicon (M1/M2/M3/M4) chips. This tool combines local language models for content generation with text-to-speech to create complete audiobooks without cloud services.

## Features

✅ **100% Local & Private** - Everything runs on your Mac, no cloud API calls
✅ **Multiple LLM Backends** - Ollama, MLX, or llama.cpp
✅ **Multiple TTS Options** - macOS built-in voices or Piper TTS
✅ **Story Generation** - Create original stories from prompts
✅ **Text Conversion** - Convert existing text files to audiobooks
✅ **Chapter Support** - Multi-chapter audiobooks with automatic splitting
✅ **Multiple Formats** - Output as MP3, M4B, or WAV
✅ **Apple Silicon Optimized** - Leverages Metal acceleration for fast inference

## Quick Start

### 1. Install Ollama (Recommended - Easiest)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (recommended: llama3.2:3b for fast generation)
ollama pull llama3.2:3b
```

### 2. Install Python Dependencies

```bash
pip install pydub

# Optional: Install ffmpeg for better audio processing
brew install ffmpeg
```

### 3. Generate Your First Audiobook

```bash
# Simple example - generates a 3-chapter mystery story
python local_audiobook_generator.py --prompt "A detective cat solves a mystery in a small town" --chapters 3
```

This will:
1. Generate a 3-chapter story using local LLM
2. Convert each chapter to speech using macOS voice
3. Combine chapters into `audiobook.mp3`
4. Save the text version as `audiobook.txt`

## Installation Options

### Option 1: Ollama (Recommended)

Easiest to set up, great performance, works out of the box.

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2:3b      # Fast, good quality (2GB)
ollama pull mistral:7b        # Better quality (4GB)
ollama pull llama3.1:8b       # Best quality (4.7GB)

# Install Python deps
pip install pydub
brew install ffmpeg
```

### Option 2: MLX (Apple Silicon Native)

Native Apple Silicon implementation, excellent performance.

```bash
# Install MLX
pip install mlx-lm pydub

# Models will be downloaded automatically from HuggingFace
# Example: mlx-community/Mistral-7B-Instruct-v0.2-4bit
```

### Option 3: llama.cpp

Flexible, supports many model formats.

```bash
# Install llama-cpp-python with Metal support
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python pydub

# Download a GGUF model manually from HuggingFace
# Place it in a known location and reference the path
```

## Usage Examples

### Generate Original Stories

```bash
# Short story (3 chapters)
python local_audiobook_generator.py \
  --prompt "A space explorer discovers an ancient alien civilization" \
  --chapters 3 \
  --output space_story.mp3

# Longer story with more chapters
python local_audiobook_generator.py \
  --prompt "A chef opens a magical restaurant where food grants wishes" \
  --chapters 10 \
  --words-per-chapter 800 \
  --output magical_chef.mp3

# Mystery with custom voice
python local_audiobook_generator.py \
  --prompt "A librarian finds a book that predicts the future" \
  --chapters 5 \
  --voice "Alex" \
  --output mystery_book.mp3
```

### Convert Existing Text to Audiobook

```bash
# Convert a text file
python local_audiobook_generator.py \
  --input my_story.txt \
  --output my_audiobook.mp3

# With custom voice and format
python local_audiobook_generator.py \
  --input novel.txt \
  --voice "Samantha" \
  --format m4b \
  --output novel.m4b
```

### Using Different Models

```bash
# Ollama with different models
python local_audiobook_generator.py \
  --model-backend ollama \
  --model mistral:7b \
  --prompt "A mystery story" \
  --output mystery.mp3

# MLX with 4-bit quantized model (faster)
python local_audiobook_generator.py \
  --model-backend mlx \
  --model mlx-community/Mistral-7B-Instruct-v0.2-4bit \
  --prompt "A sci-fi adventure" \
  --output scifi.mp3

# llama.cpp with local GGUF file
python local_audiobook_generator.py \
  --model-backend llamacpp \
  --model /path/to/model.gguf \
  --prompt "A fantasy tale" \
  --output fantasy.mp3
```

### Voice Options

```bash
# List available macOS voices
python local_audiobook_generator.py --list-voices

# Use different voices
python local_audiobook_generator.py --voice "Alex" --input story.txt      # Male voice
python local_audiobook_generator.py --voice "Samantha" --input story.txt  # Female voice
python local_audiobook_generator.py --voice "Karen" --input story.txt     # Australian
python local_audiobook_generator.py --voice "Daniel" --input story.txt    # British
```

### Advanced Options

```bash
# High creativity (higher temperature)
python local_audiobook_generator.py \
  --prompt "A surreal dream sequence" \
  --temperature 0.9 \
  --chapters 3

# More concise chapters
python local_audiobook_generator.py \
  --prompt "Flash fiction collection" \
  --chapters 10 \
  --words-per-chapter 500

# No chapter title announcements
python local_audiobook_generator.py \
  --prompt "Poetry collection" \
  --no-chapter-titles \
  --chapters 5
```

## Command-Line Options

```
--prompt, -p          Story prompt for generation
--input, -i           Input text file to convert to audiobook
--output, -o          Output audio file (default: audiobook.mp3)

--model-backend       LLM backend: ollama, mlx, llamacpp (default: ollama)
--model, -m           Model name or path (default: llama3.2:3b)

--tts-backend         TTS backend: macos, piper (default: macos)
--voice, -v           Voice name (default: Samantha)

--chapters, -c        Number of chapters to generate (default: 3)
--words-per-chapter   Target words per chapter (default: 1000)
--temperature, -t     Generation temperature 0.0-1.0 (default: 0.7)

--format, -f          Output format: mp3, m4b, wav (default: mp3)
--no-chapter-titles   Don't announce chapter titles in audio

--list-voices         List available macOS voices and exit
```

## Recommended Models

### For Ollama

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `llama3.2:3b` | 2GB | ⚡️⚡️⚡️ | ⭐️⭐️⭐️ | Quick stories, testing |
| `mistral:7b` | 4GB | ⚡️⚡️ | ⭐️⭐️⭐️⭐️ | Balanced quality/speed |
| `llama3.1:8b` | 4.7GB | ⚡️⚡️ | ⭐️⭐️⭐️⭐️⭐️ | Best quality |
| `dolphin-mixtral:8x7b` | 26GB | ⚡️ | ⭐️⭐️⭐️⭐️⭐️ | Creative stories (needs RAM) |

### For MLX

```bash
# Small, fast models (good for testing)
mlx-community/Mistral-7B-Instruct-v0.2-4bit
mlx-community/Meta-Llama-3-8B-Instruct-4bit

# Larger, higher quality
mlx-community/Mixtral-8x7B-Instruct-v0.1-4bit
```

## macOS Voice Recommendations

Popular voices for audiobooks:

- **Samantha** - Clear, pleasant female voice (US)
- **Alex** - Natural male voice (US)
- **Daniel** - British male voice
- **Karen** - Australian female voice
- **Moira** - Irish female voice
- **Fiona** - Scottish female voice

## Performance Tips

### Speed Optimization

1. **Use smaller models**: `llama3.2:3b` is 3-5x faster than `llama3.1:8b`
2. **Reduce words per chapter**: `--words-per-chapter 500` generates faster
3. **Use MLX**: Native Apple Silicon for best performance
4. **Lower temperature**: `--temperature 0.5` generates faster

### Quality Optimization

1. **Use larger models**: `llama3.1:8b` or `mistral:7b`
2. **Increase words per chapter**: `--words-per-chapter 1500`
3. **Adjust temperature**: `0.7-0.8` for creative stories
4. **Choose quality voices**: Samantha, Alex are high quality

### Memory Usage

- **8GB RAM**: Use 3B-7B models
- **16GB RAM**: Use 7B-8B models comfortably
- **32GB+ RAM**: Can use larger models like Mixtral 8x7B

## Workflow Examples

### Create a Full Novel

```bash
# Generate a 20-chapter novel
python local_audiobook_generator.py \
  --prompt "A time traveler accidentally changes history and must fix it" \
  --chapters 20 \
  --words-per-chapter 1200 \
  --model mistral:7b \
  --voice "Samantha" \
  --output time_travel_novel.mp3

# This will take 20-40 minutes depending on your Mac
# Output: time_travel_novel.mp3 (audio) + time_travel_novel.txt (text)
```

### Convert Your Own Writing

```bash
# You have a story in story.txt with chapter markers
python local_audiobook_generator.py \
  --input my_novel.txt \
  --voice "Daniel" \
  --format m4b \
  --output my_novel.m4b
```

### Batch Generate Short Stories

```bash
# Generate multiple short stories
for prompt in "A robot learns to love" "A ghost haunts a coffee shop" "A wizard loses their magic"
do
    python local_audiobook_generator.py \
      --prompt "$prompt" \
      --chapters 1 \
      --words-per-chapter 2000 \
      --output "$(echo $prompt | tr ' ' '_').mp3"
done
```

## Troubleshooting

### "Ollama not found"

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

### "Model not found"

```bash
# Pull the model first
ollama pull llama3.2:3b

# List available models
ollama list
```

### Audio conversion issues

```bash
# Install ffmpeg
brew install ffmpeg

# Install pydub
pip install pydub
```

### Generation is slow

- Use a smaller model: `llama3.2:3b`
- Reduce words per chapter: `--words-per-chapter 500`
- Reduce number of chapters: `--chapters 3`

### Out of memory

- Use a smaller model
- Close other applications
- Reduce context with fewer chapters

### Voice sounds robotic

- macOS built-in voices are high quality but may sound synthetic
- Try different voices: `python local_audiobook_generator.py --list-voices`
- For more natural voices, consider commercial TTS services (requires cloud)

## Technical Details

### How It Works

1. **Text Generation**: Uses local LLM to generate story chapters
2. **Chapter Processing**: Splits content, adds titles, formats text
3. **Text-to-Speech**: Converts each chapter to audio using TTS engine
4. **Audio Combining**: Merges chapter audio files with transitions
5. **Export**: Outputs final audiobook in chosen format

### File Outputs

```
audiobook.mp3      # Final audiobook
audiobook.txt      # Text version with all chapters
chapter_01.aiff    # Temporary chapter audio (deleted)
chapter_02.aiff    # Temporary chapter audio (deleted)
...
```

### Supported Formats

- **MP3**: Universal, good compression
- **M4B**: Audiobook format, supports chapters
- **WAV**: Uncompressed, large files

## Privacy & Ethics

✅ **Private**: All processing happens locally, no data sent to cloud
✅ **No tracking**: No telemetry or usage tracking
✅ **Open source models**: Uses open-source LLMs
✅ **Fair use**: For personal use and learning

**Important**:
- Generated content is AI-created, review before sharing
- Respect copyright when converting existing texts
- Commercial use may require additional licensing

## Contributing

Improvements welcome! Areas for enhancement:

- Additional TTS backends (Bark, Coqui TTS)
- Better chapter detection algorithms
- Audio effects (background music, sound effects)
- Character voice mapping
- GUI interface

## License

This script is provided as-is for personal and educational use.

## Resources

- [Ollama](https://ollama.com) - Easy local LLM runner
- [MLX](https://github.com/ml-explore/mlx) - Apple's ML framework
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - LLM inference in C++
- [Piper TTS](https://github.com/rhasspy/piper) - Fast local TTS

## Examples Gallery

### Example 1: Quick Test

```bash
python local_audiobook_generator.py \
  --prompt "A cat becomes a detective" \
  --chapters 1 \
  --words-per-chapter 500
```

**Time**: ~2 minutes
**Output**: 500-word short story as MP3

### Example 2: Standard Audiobook

```bash
python local_audiobook_generator.py \
  --prompt "A young wizard discovers a hidden magical library" \
  --chapters 10 \
  --words-per-chapter 1000 \
  --model mistral:7b \
  --voice "Samantha"
```

**Time**: ~20-30 minutes
**Output**: ~10,000 word audiobook (~1 hour audio)

### Example 3: Converting Your Novel

```bash
python local_audiobook_generator.py \
  --input my_50000_word_novel.txt \
  --voice "Alex" \
  --format m4b \
  --output my_audiobook.m4b
```

**Time**: ~10-15 minutes (TTS only)
**Output**: Full audiobook from your text

---

**Made with ❤️ for Apple Silicon**
*Turn your M-series Mac into an audiobook production studio!*
