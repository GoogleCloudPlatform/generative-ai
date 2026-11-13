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

package livebridge

import (
	"encoding/base64"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"

	"google.golang.org/genai"
)

// Validation bounds shared across Live session configurations and image endpoints.
const (
	MaxImagePromptChars     = 10000
	MaxAdaptationPhrases    = 100
	MaxAdaptationPhraseLen  = 200
	MaxRealtimeAudioMIMELen = 64
	MaxLoggedValueRunes     = 40
)

var (
	// AvatarImageMIMETypes lists image formats accepted for custom avatars and
	// reference images. WebP is excluded because image synthesis rejects it
	// with 1011 internal error.
	AvatarImageMIMETypes = map[string]bool{
		"image/png":  true,
		"image/jpeg": true,
	}

	// RealtimeVideoMIMETypes lists image formats accepted for realtime vision
	// frames and pre-response tool snapshots.
	RealtimeVideoMIMETypes = map[string]bool{
		"image/jpeg": true,
		"image/png":  true,
	}

	// ValidStartSensitivity enumerates accepted start-of-speech VAD overrides.
	ValidStartSensitivity = map[string]bool{
		string(genai.StartSensitivityHigh): true,
		string(genai.StartSensitivityLow):  true,
	}

	// ValidEndSensitivity enumerates accepted end-of-speech VAD overrides.
	ValidEndSensitivity = map[string]bool{
		string(genai.EndSensitivityHigh): true,
		string(genai.EndSensitivityLow):  true,
	}

	// ValidActivityHandling enumerates accepted barge-in handling modes.
	ValidActivityHandling = map[string]bool{
		string(genai.ActivityHandlingStartOfActivityInterrupts): true,
		string(genai.ActivityHandlingNoInterruption):            true,
	}

	presetNamePattern   = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_-]{0,63}$`)
	languageCodePattern = regexp.MustCompile(`^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,3}$`)
	errNotDataURL       = errors.New(`expected a "data:<mime>;base64,<data>" URL`)
)

// ParseImageDataURL decodes a base64 data URL and verifies its MIME type
// against allowed.
func ParseImageDataURL(s string, allowed map[string]bool) (mime string, data []byte, err error) {
	rest, ok := strings.CutPrefix(strings.TrimSpace(s), "data:")
	if !ok {
		return "", nil, errNotDataURL
	}
	header, payload, ok := strings.Cut(rest, ",")
	if !ok {
		return "", nil, errNotDataURL
	}
	mediaType, params, _ := strings.Cut(header, ";")
	if !strings.Contains(";"+params+";", ";base64;") {
		return "", nil, errNotDataURL
	}
	mime = strings.ToLower(strings.TrimSpace(mediaType))
	if !allowed[mime] {
		return "", nil, fmt.Errorf("unsupported image type %q (use PNG or JPEG)", mime)
	}
	data, err = base64.StdEncoding.DecodeString(payload)
	if err != nil {
		return "", nil, fmt.Errorf("decode base64 image: %w", err)
	}
	if len(data) == 0 {
		return "", nil, errors.New("image data is empty")
	}
	return mime, data, nil
}

// TruncateRunes caps s at maxRunes UTF-8 code points without splitting
// multi-byte sequences.
func TruncateRunes(s string, maxRunes int) string {
	if utf8.RuneCountInString(s) <= maxRunes {
		return s
	}
	n := 0
	for i := range s {
		if n == maxRunes {
			return s[:i]
		}
		n++
	}
	return s
}

// ValidPresetName reports whether s is a safe preset avatar or voice identifier.
func ValidPresetName(s string) bool { return presetNamePattern.MatchString(s) }

// ValidLanguageCode reports whether s is a valid BCP-47-style language tag.
func ValidLanguageCode(s string) bool { return languageCodePattern.MatchString(s) }

// ValidRealtimeAudioMIME reports whether s is an accepted PCM audio MIME type
// ("audio/pcm" or "audio/pcm;rate=16000").
func ValidRealtimeAudioMIME(s string) bool {
	if len(s) > MaxRealtimeAudioMIMELen {
		return false
	}
	base, params, _ := strings.Cut(strings.ToLower(strings.TrimSpace(s)), ";")
	if base != "audio/pcm" {
		return false
	}
	return params == "" || ParsePCMSampleRate(s) > 0
}

// ParsePCMSampleRate extracts the numeric sample rate from a MIME type such as
// "audio/pcm;rate=24000", returning 0 when absent or invalid.
func ParsePCMSampleRate(mime string) int {
	const marker = "rate="
	idx := strings.Index(strings.ToLower(mime), marker)
	if idx == -1 {
		return 0
	}
	rateStr := mime[idx+len(marker):]
	if end := strings.IndexAny(rateStr, ";, "); end != -1 {
		rateStr = rateStr[:end]
	}
	var rate int
	if _, err := fmt.Sscanf(rateStr, "%d", &rate); err != nil || rate <= 0 {
		return 0
	}
	return rate
}

// InRange reports whether an optional float32 pointer lies within [lo, hi].
func InRange(v *float32, lo, hi float32) bool {
	return v == nil || (*v >= lo && *v <= hi)
}

// SupportsProactiveAudio reports whether model supports
// ProactivityConfig.ProactiveAudio without rejecting setup with 1007.
func SupportsProactiveAudio(model, fallbackModel string) bool {
	if strings.TrimSpace(model) == "" {
		model = fallbackModel
	}
	return strings.Contains(model, "3.8") || strings.Contains(model, "lite")
}
