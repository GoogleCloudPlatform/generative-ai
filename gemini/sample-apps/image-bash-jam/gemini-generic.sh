#!/bin/bash

# Usage: $0 <IMAGE> <question on that image>
# Give it an image in input and ask a question after it :)
#

set -euo pipefail

# common functions
source _common.sh

if [ -f .envrc ]; then
    source .envrc
else
    _red "Warning: PROJECT_ID might not be set, make sure you put it in .envrc:"
    echo '1. cp .envrc.dist .envrc # copy from template'
    echo '2. vim .envrc            # edit away'
    echo "PROJECT_ID: $PROJECT_ID"
fi

#PROJECT_ID='...' # Needs to be provided from ``.envrc` or in some other way
MODEL_ID="gemini-pro-vision"
LOCATION=us-central1
TMP_OUTPUT_FILE=.tmp.lastresponse-generic.json
REQUEST_FILE=.tmp.lastrequest-generic.json
JQ_PATH=".[0].candidates[0].content.parts[0].text" # PROD_URL_SELECTOR first answer
JQ_PATH_PLURAL=".[].candidates[0].content.parts[0].text" # PROD_URL_SELECTOR all answers
#STAGING_JQ_PATH=".candidates[0].content.parts[0].text" # STAGING_URL_SELECTOR (changed! Why?)
GENERATE_MP3="${GENERATE_MP3:-unknown}"
TEMPERATURE="${TEMPERATURE:-0.2}"

function _usage() {
    echo "Usage: $0 <IMAGE> <question on that image>"
    echo "Example: $0 image.jpg \"what do you see here?\""
    echo "Error: $1"
    exit 1
}


if [ $# -lt 2 ] ; then
    _usage "Provide at least 2 arguments (TODO just 1)"

fi

export IMAGE="$1"
data=$(_base64_encode_mac_or_linux "$IMAGE") # Mac or Linux should both work!
shift
export ORIGINAL_QUESTION="$@" # should default to "what do you see here?"
export QUESTION="$(echo "$@" | sed "s/'/ /g")" # cleaned up

echo "# 🤌  QUESTION: $(_yellow $QUESTION)"
echo "# 🌡️  TEMPERATURE: $TEMPERATURE "
echo "# 👀 Examining image $(_white $(file "$IMAGE")). "


#echo "💾 Find any errors in: $TMP_OUTPUT_FILE"

    #  "generation_config":{
    #     "temperature": $TEMPERATURE,
    #     "top_p": 0.1,
    #     "top_k": 16,
    #     "max_output_tokens": 2048,
    #     "candidate_count": 1,
    #     "stop_sequences": [],
    #     },

cat > "$REQUEST_FILE" <<EOF
{ "contents": {
      "role": "USER",
      "parts": [
        {"text": '$QUESTION'},
        {"inline_data": {
            "data": '$data',
            "mime_type": "image/jpeg"}}
      ]
  },
  "safety_settings": {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_LOW_AND_ABOVE"
  },
  "generation_config": {
        "temperature": 0.2,
        "topP": 0.8,
        "topK": 40,
        "maxOutputTokens": 800
  }
}
EOF
# "stopSequences": [".", "?", "!"]
STAGING_URL="https://${LOCATION}-autopush-aiplatform.sandbox.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/$MODEL_ID:generateContent"
PROD_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/$MODEL_ID:streamGenerateContent"

curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json"  \
    "$PROD_URL" -d \
    @"$REQUEST_FILE" \
    > $TMP_OUTPUT_FILE 2>t ||
        show_errors_and_exit

OUTPUT=$(cat $TMP_OUTPUT_FILE | jq "$JQ_PATH" || echo jq-error) # this

if [ "$OUTPUT" = '""' -o "$OUTPUT" = 'null' -o "$OUTPUT" = 'jq-error' ]; then # empty answer
    echo "#😥 Sorry, some error here. Dig into the JSON file more: $TMP_OUTPUT_FILE" >&2
    cat $TMP_OUTPUT_FILE | jq >&2
else
    N_CANDIDATES=$(cat $TMP_OUTPUT_FILE | jq "$JQ_PATH_PLURAL" -r | wc -l)
    echo -e "# ♊ Gemini no Saga answer for you ($N_CANDIDATES candidates):"
    cat $TMP_OUTPUT_FILE | jq "$JQ_PATH_PLURAL" -r | xargs -0 | _lolcat
    if [ "true" = "$GENERATE_MP3" ]; then
        ./tts.sh `cat $TMP_OUTPUT_FILE | jq "$JQ_PATH" -r`
        cp t.mp3 "$IMAGE".mp3
    else
        echo "# Note: No mp3 file generated (use GENERATE_MP3=true to generate one)"
    fi
fi


