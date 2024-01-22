#!/bin/bash

DEFAULT_INPUT_DIR="images/"
INPUT_DIR="${1:-$DEFAULT_INPUT_DIR}"

echo "I'm going to annotate with images and audio all image files in DIR: $INPUT_DIR"
for F in "$INPUT_DIR"/*.{jpeg,png,gif,jpg}  ; do
    if [ -f $F ] ; then
        ANNOTATION_FILE="$F.explain.txt"
        echo $F
        if [ -f "$ANNOTATION_FILE" ] ; then
            echo File exists, skipping: "$ANNOTATION_FILE"
        else
            GENERATE_MP3=true ./gemini-explain-image.sh "$F" | tee "$ANNOTATION_FILE"
        fi
    fi
done
