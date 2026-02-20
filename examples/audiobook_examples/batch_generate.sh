#!/bin/bash
# Batch Story Generator - Generate multiple short stories as audiobooks

echo "📚 Batch Story Generator"
echo "========================"
echo ""
echo "Generate multiple short stories as audiobooks from a list of prompts."
echo ""

# Story prompts (one per line)
read -r -d '' PROMPTS << 'EOF'
A robot learns to paint and discovers the meaning of beauty
A ghost haunts a coffee shop but only appears to sad customers
A wizard loses their magic and must solve problems without it
A detective cat solves the mystery of the missing fish
An AI falls in love with a human through their chat conversations
A time-frozen city where only one person can still move
A library where books come alive at midnight
A chef whose food can heal emotional wounds
An astronaut discovers a message from Earth's future
A musician who can play emotions into reality
EOF

# Default settings
MODEL="llama3.2:3b"
VOICE="Samantha"
CHAPTERS=1
WORDS=800
OUTPUT_DIR="batch_audiobooks"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Settings:"
echo "  Model: $MODEL"
echo "  Voice: $VOICE"
echo "  Chapters per story: $CHAPTERS"
echo "  Words per chapter: $WORDS"
echo "  Output directory: $OUTPUT_DIR"
echo ""

# Count stories
STORY_COUNT=$(echo "$PROMPTS" | grep -c '^')
echo "Found $STORY_COUNT story prompts"
echo ""

read -p "Generate all $STORY_COUNT audiobooks? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting batch generation..."
echo ""

# Counter
COUNT=0
SUCCESS=0
FAILED=0

# Read prompts and generate
while IFS= read -r prompt; do
    # Skip empty lines
    [ -z "$prompt" ] && continue

    COUNT=$((COUNT + 1))

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$COUNT/$STORY_COUNT] Generating: $prompt"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Create filename from prompt
    FILENAME=$(echo "$prompt" | tr '[:upper:]' '[:lower:]' | tr -s ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-50)
    OUTPUT="$OUTPUT_DIR/${FILENAME}.mp3"

    # Generate audiobook
    python ../../local_audiobook_generator.py \
        --prompt "$prompt" \
        --chapters "$CHAPTERS" \
        --words-per-chapter "$WORDS" \
        --model "$MODEL" \
        --voice "$VOICE" \
        --output "$OUTPUT"

    if [ $? -eq 0 ]; then
        echo "✅ Success: $OUTPUT"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌ Failed: $prompt"
        FAILED=$((FAILED + 1))
    fi

    echo ""
done <<< "$PROMPTS"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Batch Generation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total: $COUNT stories"
echo "✅ Success: $SUCCESS"
echo "❌ Failed: $FAILED"
echo ""
echo "Audiobooks saved in: $OUTPUT_DIR/"
echo ""
echo "To play all:"
echo "  open $OUTPUT_DIR/*.mp3"
