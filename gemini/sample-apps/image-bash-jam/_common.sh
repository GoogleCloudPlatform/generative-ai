#!/bin/bash
#
# Note: this is a shell script to be included in all other scripts. It subsumes common functionality
#       across shell scripts in most other shell scripts.
# Encode (used to encode image to give to Gemini)
function _base64_encode_mac_or_linux() {
    IMAGE="$1"
    #data=$(base64 -i "$IMAGE" -o -) # Mac
    #data=$(base64 -w 0 "$IMAGE") # linux
    if [[ $(uname) == "Darwin" ]] ; then
        base64 -i "$IMAGE" -o -
    else
        base64 -w 0 "$IMAGE"
    fi
}

# Decode (used in TTS to decode MP3)
function _base64_decode_mac_or_linux() {
    IMAGE="$1"
    if [[ $(uname) == "Darwin" ]] ; then
        base64 --decode -i "$IMAGE" -o -
    else
        base64 "$IMAGE" --decode
    fi
}


# assumes you have the output in file 't'
function show_errors_and_exit() {
    echo Woops. Some Errors found. See error in t:
    _redden < t # cat t | _redden
    exit 42
}

function _red() {
    echo -en "\033[1;31m$*\033[0m\n"
}
# make the STD in RED :) (proper bash filter)
function _redden() {
    while read -r row; do echo -en "\033[0;31m$row\033[0m\n"; done
}
function _green() {
    echo -en "\033[1;32m$*\033[0m\n"
}
function _white() {
    echo -en "\033[1;37m$*\033[0m\n"
}
function _yellow() {
    echo -en "\033[1;33m$*\033[0m\n"
}
# If you dont have lolcat your life is going to be more miserable.
# To fix your life: `gem install lolcat`
function _lolcat() {
    if which lolcat >/dev/null ; then
        lolcat
    else
        cat
    fi
}
