#!/bin/bash

# set -euo pipefail

# alternatively, an even pickier question on 🇮🇹 Italianity of the picture
#./gemini-generic.sh "$1" "Descrivimi cosa vedi in questa immagine e se ci sono c'e' correlazione alcuna con l'Italia come nazione e come cultura italiana"
TTS_LANG='it-IT' ./gemini-generic.sh "$1" "Descrivimi questa immagine"
