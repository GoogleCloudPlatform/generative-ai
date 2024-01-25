#!/bin/bash

##############################################################################
# word to text via CURL :)
# Docs https://cloud.google.com/text-to-speech/docs/create-audio-text-command-line
# Before you run, pls execute:
#
# 	gcloud auth application-default login
# 	gcloud auth application-default set-quota-project "$PROJECT_ID"
#
##############################################################################
# # https://cloud.google.com/text-to-speech/docs/create-audio-text-command-line
# Sample JSON for TTS to help understand the script:
# {
#   "input": {
#     "text": "ciao mamma, butta la pasta"
#   },
#   "voice": {
#     "languageCode": "en-US",
#     "ssmlGender": "FEMALE"
#   },
#   "audioConfig": {
#     "audioEncoding": "MP3"
#   }
# }
##############################################################################

. .envrc

set -euo pipefail

SENTENCE="${*//\'/\\\'}"        # c'e' l'uomo => "c\' e l\'uomo"
TMP_OUTPUT_FILE='.tmp.tts-output.json'
JQ_PATH='.audioContent'
# Latest model: https://cloud.google.com/text-to-speech/docs/voices
DEFAULT_LANG="en-US"          # safe choice
TTS_LANG="${TTS_LANG:-$DEFAULT_LANG}"
#DEFAULT_GENDER='MALE' doesnt work in italian -> dflt is it-IT-Neural2-A
DEFAULT_GENDER='FEMALE'

# common functions
source _common.sh

echo "# PROJECT_ID: $(_yellow $PROJECT_ID)"
echo "# TTS_LANG: $(_yellow $TTS_LANG)"
echo "# Cleaned up SENTENCE: $(_yellow $SENTENCE)"

curl -X POST \
  -H "Authorization: Bearer $(gcloud --project "$PROJECT_ID" auth print-access-token)" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  -H "Content-Type: application/json" \
  -d "{
    'input': {
      'text': '$SENTENCE'
    },
    'voice': {
      'languageCode': '$TTS_LANG',
      'ssmlGender': '$DEFAULT_GENDER'
    },
    'audioConfig': {
      'audioEncoding': 'MP3'
    }
  }" "https://texttospeech.googleapis.com/v1/text:synthesize" \
    > $TMP_OUTPUT_FILE 2>t ||
        show_errors_and_exit

echo "Written $TMP_OUTPUT_FILE. curl_ret=$?"

cat $TMP_OUTPUT_FILE | jq -r "$JQ_PATH" > t.audio.encoded
_base64_decode_mac_or_linux t.audio.encoded > t.mp3
# i need te LAST so i can copy it deterministically from other script :)
cp t.mp3 "t.${SENTENCE:0:50}.mp3"




file t.audio* t.mp3

if file t.mp3 | grep 'MPEG ADTS, layer III' ; then
  _green "All good. MP3 created: 't.${SENTENCE:0:50}.mp3'"
else
  _red "# OOps, some errors, I couldnt create a proper MP3 file. Check the encoding and the quotes in the input."
  cat "$TMP_OUTPUT_FILE"
  exit 255
fi
