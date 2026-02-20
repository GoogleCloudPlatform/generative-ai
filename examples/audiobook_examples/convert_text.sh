#!/bin/bash
# Convert Text to Audiobook - Convert existing text file to audiobook

echo "📖 Text to Audiobook Converter"
echo "=============================="
echo ""

# Check if input file provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_text_file> [--voice VoiceName] [--format mp3|m4b|wav]"
    echo ""
    echo "Example:"
    echo "  $0 my_story.txt"
    echo "  $0 my_story.txt --voice Alex --format m4b"
    exit 1
fi

INPUT="$1"
shift

# Check if file exists
if [ ! -f "$INPUT" ]; then
    echo "❌ Error: File not found: $INPUT"
    exit 1
fi

# Default values
VOICE="Samantha"
FORMAT="mp3"
OUTPUT="${INPUT%.*}.${FORMAT}"

# Parse remaining arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --voice)
            VOICE="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            OUTPUT="${INPUT%.*}.${FORMAT}"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get word count
WORD_COUNT=$(wc -w < "$INPUT")

echo "Input file: $INPUT"
echo "Word count: ~$WORD_COUNT words"
echo "Voice: $VOICE"
echo "Format: $FORMAT"
echo "Output: $OUTPUT"
echo ""
echo "Estimated audio duration: ~$((WORD_COUNT / 150)) minutes"
echo ""

read -p "Convert to audiobook? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🎙️ Converting to audiobook..."
echo ""

# Run the converter
python ../../local_audiobook_generator.py \
    --input "$INPUT" \
    --voice "$VOICE" \
    --format "$FORMAT" \
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
else
    echo ""
    echo "❌ Conversion failed. Check the error messages above."
    exit 1
fi
