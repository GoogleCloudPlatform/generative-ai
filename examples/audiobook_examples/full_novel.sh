#!/bin/bash
# Full Novel Generator - Creates a multi-chapter audiobook

echo "📚 Full Novel Audiobook Generator"
echo "================================="
echo ""
echo "This will generate a full multi-chapter novel as an audiobook."
echo "⏱️  This may take 20-40 minutes depending on settings."
echo ""

# Default values
PROMPT="A time traveler accidentally changes history and must fix the timeline"
CHAPTERS=10
WORDS=1000
MODEL="llama3.2:3b"
VOICE="Samantha"
OUTPUT="novel.mp3"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
            shift 2
            ;;
        --chapters)
            CHAPTERS="$2"
            shift 2
            ;;
        --words)
            WORDS="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --voice)
            VOICE="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--prompt \"...\"] [--chapters N] [--words N] [--model NAME] [--voice NAME] [--output FILE]"
            exit 1
            ;;
    esac
done

echo "Story Prompt: $PROMPT"
echo "Chapters: $CHAPTERS"
echo "Words per chapter: $WORDS"
echo "Model: $MODEL"
echo "Voice: $VOICE"
echo "Output: $OUTPUT"
echo ""
echo "Estimated total words: ~$((CHAPTERS * WORDS))"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting generation..."
echo ""

# Run the generator
python ../../local_audiobook_generator.py \
    --prompt "$PROMPT" \
    --chapters "$CHAPTERS" \
    --words-per-chapter "$WORDS" \
    --model "$MODEL" \
    --voice "$VOICE" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Success! Your audiobook is ready: $OUTPUT"
    echo ""

    # Get file size
    SIZE=$(du -h "$OUTPUT" | cut -f1)
    echo "File size: $SIZE"
    echo ""

    echo "To play it:"
    echo "  open $OUTPUT"
    echo ""
    echo "Text version saved to: ${OUTPUT%.mp3}.txt"
else
    echo ""
    echo "❌ Generation failed. Check the error messages above."
    exit 1
fi
