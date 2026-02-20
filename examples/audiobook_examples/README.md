# Audiobook Generation Examples

This directory contains example scripts for generating audiobooks using local LLMs on Apple Silicon.

## Prerequisites

1. **Install Ollama** (recommended):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.2:3b
   ```

2. **Install dependencies**:
   ```bash
   pip install pydub
   brew install ffmpeg
   ```

3. **Make scripts executable**:
   ```bash
   chmod +x *.sh
   ```

## Quick Start Examples

### 1. Quick Story (1-2 minutes)

Generate a short single-chapter story:

```bash
./quick_story.sh
```

Custom prompt:
```bash
./quick_story.sh --prompt "A dragon learns to bake cookies"
```

With different voice:
```bash
./quick_story.sh --prompt "A mystery in space" --voice "Alex"
```

**Output**: `quick_story.mp3` + `quick_story.txt`

---

### 2. Full Novel (20-40 minutes)

Generate a multi-chapter novel:

```bash
./full_novel.sh
```

Custom 5-chapter mystery:
```bash
./full_novel.sh \
  --prompt "A detective solves a crime on a cruise ship" \
  --chapters 5 \
  --words 1200
```

Longer novel with better model:
```bash
./full_novel.sh \
  --prompt "An epic fantasy quest to save the kingdom" \
  --chapters 20 \
  --words 1500 \
  --model mistral:7b
```

**Output**: `novel.mp3` + `novel.txt`

---

### 3. Convert Text File

Convert your existing text to audiobook:

```bash
./convert_text.sh my_story.txt
```

With custom voice and format:
```bash
./convert_text.sh my_novel.txt --voice "Daniel" --format m4b
```

**Output**: `my_story.mp3` (or specified format)

---

### 4. Batch Generate

Generate multiple short stories at once:

```bash
./batch_generate.sh
```

Edit the script to customize the prompts. The default generates 10 different short stories.

**Output**: `batch_audiobooks/` directory with multiple MP3 files

---

## Available Voices

List all available macOS voices:

```bash
python ../../local_audiobook_generator.py --list-voices
```

Popular choices:
- **Samantha** - Clear female voice (US)
- **Alex** - Natural male voice (US)
- **Daniel** - British male
- **Karen** - Australian female
- **Fiona** - Scottish female

## Models Comparison

### Fast Generation (Testing)
```bash
--model llama3.2:3b
```
- Size: 2GB
- Speed: ⚡⚡⚡ Very fast
- Quality: ⭐⭐⭐ Good
- Best for: Testing, short stories

### Balanced (Recommended)
```bash
--model mistral:7b
```
- Size: 4GB
- Speed: ⚡⚡ Fast
- Quality: ⭐⭐⭐⭐ Very good
- Best for: Full novels

### High Quality
```bash
--model llama3.1:8b
```
- Size: 4.7GB
- Speed: ⚡⚡ Moderate
- Quality: ⭐⭐⭐⭐⭐ Excellent
- Best for: Final productions

## Customization Examples

### More Creative Stories
```bash
./full_novel.sh \
  --prompt "A surreal dreamscape adventure" \
  --temperature 0.9
```

### Concise Chapters
```bash
./full_novel.sh \
  --prompt "Flash fiction collection" \
  --chapters 10 \
  --words 500
```

### Different Genre
```bash
# Mystery
./full_novel.sh --prompt "A locked room murder mystery"

# Sci-Fi
./full_novel.sh --prompt "First contact with aliens"

# Fantasy
./full_novel.sh --prompt "A quest to find the lost magic"

# Romance
./full_novel.sh --prompt "Two rivals slowly fall in love"

# Horror
./full_novel.sh --prompt "A haunted house reveals its secrets"
```

## Workflow Tips

### 1. Test First
Always test with a quick story before committing to a full novel:
```bash
./quick_story.sh --prompt "Your story idea"
```

### 2. Save Text Separately
The text version is automatically saved. Review it before listening:
```bash
cat novel.txt
```

### 3. Edit Then Convert
Generate text first, edit it, then convert to audio:
```bash
# Generate
./full_novel.sh --prompt "Your idea"

# Edit novel.txt manually

# Convert edited version
./convert_text.sh novel.txt --output final_audiobook.mp3
```

### 4. Organize Output
Create a dedicated audiobooks directory:
```bash
mkdir ~/Audiobooks
mv *.mp3 ~/Audiobooks/
```

## Troubleshooting

### Script won't run
```bash
chmod +x *.sh
```

### "Ollama not found"
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

### Generation is slow
- Use smaller model: `--model llama3.2:3b`
- Reduce words: `--words 500`
- Fewer chapters: `--chapters 3`

### Audio quality issues
- Try different voice: `--voice "Alex"`
- Install ffmpeg: `brew install ffmpeg`

## Performance Guide

**On M1/M2 (8GB RAM)**:
- Use `llama3.2:3b` or `mistral:7b`
- 3-5 chapters recommended
- 500-1000 words per chapter

**On M1/M2/M3 Pro (16GB+ RAM)**:
- Use any model up to `llama3.1:8b`
- 10-20 chapters comfortable
- 1000-1500 words per chapter

**On M1/M2/M3 Max (32GB+ RAM)**:
- Can use larger models
- 20+ chapters
- 1500-2000 words per chapter

## Next Steps

After getting comfortable with these examples:

1. **Modify prompts** in the scripts to match your interests
2. **Experiment with different models** to find quality/speed balance
3. **Try different voices** for various character types
4. **Create your own scripts** for specific workflows
5. **Share your audiobooks** with friends and family!

## Support

For issues or questions:
- Check the main README: `../../LOCAL_AUDIOBOOK_README.md`
- Review the script source code
- Test with the simple quick_story.sh first

---

**Happy Audiobook Generation! 🎙️📚**
