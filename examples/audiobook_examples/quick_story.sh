#!/bin/bash
# Quick Story Generator - Creates a short audiobook in ~2 minutes

echo "🎙️ Quick Story Audiobook Generator"
echo "=================================="
echo ""
echo "This will generate a short 1-chapter story (~500 words)"
echo "using a local LLM and convert it to an audiobook."
echo ""

# Default values
PROMPT="A mysterious cat discovers a hidden door in an old library"
OUTPUT="quick_story.mp3"
VOICE="Samantha"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prompt)
            PROMPT="$2"
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
            echo "Usage: $0 [--prompt \"your prompt\"] [--voice VoiceName] [--output file.mp3]"
            exit 1
            ;;
    esac
done

echo "Prompt: $PROMPT"
echo "Voice: $VOICE"
echo "Output: $OUTPUT"
echo ""

# Run the generator
python ../../local_audiobook_generator.py \
    --prompt "$PROMPT" \
    --chapters 1 \
    --words-per-chapter 500 \
    --voice "$VOICE" \
    --output "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Success! Your audiobook is ready: $OUTPUT"
    echo ""
    echo "To play it:"
    echo "  open $OUTPUT"
else
    echo ""
    echo "❌ Generation failed. Check the error messages above."
    exit 1
fi
