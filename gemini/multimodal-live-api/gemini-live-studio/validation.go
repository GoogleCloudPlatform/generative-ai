// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import "gemini-live-studio/livebridge"

const (
	maxImagePromptChars    = livebridge.MaxImagePromptChars
	maxAdaptationPhrases   = livebridge.MaxAdaptationPhrases
	maxAdaptationPhraseLen = livebridge.MaxAdaptationPhraseLen
)

var (
	avatarImageMIMETypes  = livebridge.AvatarImageMIMETypes
	validStartSensitivity = livebridge.ValidStartSensitivity
	validEndSensitivity   = livebridge.ValidEndSensitivity
	validActivityHandling = livebridge.ValidActivityHandling
)

func parseImageDataURL(s string, allowed map[string]bool) (mime string, data []byte, err error) {
	return livebridge.ParseImageDataURL(s, allowed)
}

func truncateRunes(s string, maxRunes int) string {
	return livebridge.TruncateRunes(s, maxRunes)
}

func validPresetName(s string) bool           { return livebridge.ValidPresetName(s) }
func validLanguageCode(s string) bool         { return livebridge.ValidLanguageCode(s) }
func validRealtimeAudioMIME(s string) bool    { return livebridge.ValidRealtimeAudioMIME(s) }
func inRange(v *float32, lo, hi float32) bool { return livebridge.InRange(v, lo, hi) }
