#!/bin/bash

# images: https://www.youtube.com/watch?v=Rn30RMhEBTs&list=PL590L5WQmH8cTsUpRXyFWzIpc4ch1VksX

set -euo pipefail

source _common.sh

if [ -f .envrc ]; then
    source .envrc
fi

#PROJECT_ID='provided in .envrc'
#MODEL_ID="gemini-pro-vision" # TODO parametrize into model :)
LOCATION=us-central1
TMP_OUTPUT_FILE=.tmp.lastresponse-generic-2pix.json
REQUEST_FILE=.tmp.request-generic-2pix.json
#JQ_PATH=".[0].candidates[0].content.parts[0].text" # PROD_URL_SELECTOR
#STAGING_JQ_PATH=".candidates[0].content.parts[0].text" # STAGING_URL_SELECTOR (changed! Why?)
JQ_PATH_PLURAL=".[].candidates[0].content.parts[0].text" # PROD_URL_SELECTOR all answers

function _usage() {
    echo "Usage: $0 <IMAGE> <question on that image>"
    echo "Example: $0 image.jpg \"what do you see here?\""
    echo "Error: $1"
    exit 1
}

# function show_errors_and_exit() {
#     echo Woops. Some Errors found. See error in t:
#     cat t | _redden
#     exit 42
# }

if [ $# -lt 2 ] ; then
    _usage "Provide at least 2 arguments (TODO just 1)"

fi

export IMAGE1="$1"
export IMAGE2="$2"

data1=$(_base64_encode_mac_or_linux "$IMAGE1")
data2=$(_base64_encode_mac_or_linux "$IMAGE2")
#shift
#shift
#export QUESTION="$@" # should default to "what do you see here?"
export QUESTION="Can you highlight similarity and differences between the two? Also, do you recognize the same person in both of them?"

echo "♊️ Question: $(_yellow "$QUESTION")"
echo " 👀 Examining image1 $IMAGE1: $(_white "$(file "$IMAGE1")"). "
echo " 👀 Examining image2 $IMAGE2: $(_white "$(file "$IMAGE2")"). "
#echo "Find any errors in: $TMP_OUTPUT_FILE"

cat > "$REQUEST_FILE" <<EOF
{'contents': {
      'role': 'USER',
      'parts': [
        {'text': '$QUESTION'},
        {'inline_data': {
            'data': '$data1',
            'mime_type':'image/jpeg'}
        },
        {'inline_data': {
            'data': '$data2',
            'mime_type':'image/jpeg'}
        }
        ]},


  "safety_settings": {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_LOW_AND_ABOVE"
  },
  "generation_config": {
        "temperature": 0.2,
        "topP": 0.8,
        "topK": 40,
        "maxOutputTokens": 1500

  }
}
EOF
#"stopSequences": [".", "?", "!"]
#STAGING_URL="https://${LOCATION}-autopush-aiplatform.sandbox.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/gemini-pro-vision:generateContent"
PROD_URL="https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/gemini-pro-vision:streamGenerateContent"


curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json"  \
    "$PROD_URL" -d \
    @"$REQUEST_FILE" \
    > $TMP_OUTPUT_FILE 2>t ||
        show_errors_and_exit

#echo "Written $TMP_OUTPUT_FILE. curl_ret=$?"

OUTPUT=$(cat $TMP_OUTPUT_FILE | jq $JQ_PATH_PLURAL || echo  '""')

if [ "$OUTPUT" = '""' ]; then # empty answer
    echo "# ‼️ Sorry, some error here. Dig into the JSON file more: $TMP_OUTPUT_FILE" >&2
    cat $TMP_OUTPUT_FILE | jq >&2
else
    N_CANDIDATES=$(cat $TMP_OUTPUT_FILE | jq "$JQ_PATH_PLURAL" -r | wc -l)
    echo "# ♊️ Describing attached image ($N_CANDIDATES candidates):"
    cat $TMP_OUTPUT_FILE | jq "$JQ_PATH_PLURAL" -r | xargs -0 | _lolcat
fi
