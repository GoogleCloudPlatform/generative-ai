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

import (
	"encoding/base64"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"

	"google.golang.org/genai"
)

// Validation for client-supplied values that are forwarded to Gemini. The
// policy is: values that make the session meaningless (a broken custom avatar)
// are hard errors; optional tuning values that are malformed are logged and
// dropped so the server default applies, instead of failing setup with a 1007.

// avatarImageMIMETypes are accepted for custom avatars and reference images.
// The frontend only produces these (upload accepts image/jpeg and image/png,
// camera capture is JPEG, generated avatars come back as PNG/JPEG). WebP is
// known to fail image generation with "1011 internal error".
var avatarImageMIMETypes = map[string]bool{
	"image/png":  true,
	"image/jpeg": true,
}

// realtimeVideoMIMETypes are accepted for 1 FPS vision frames.
var realtimeVideoMIMETypes = map[string]bool{
	"image/jpeg": true,
	"image/png":  true,
}

var (
	// Preset avatar and prebuilt voice names: "Kira", "Zubenelgenubi", ...
	presetNamePattern = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_-]{0,63}$`)
	// BCP-47-style language tags: "en-US", "es-419", "zh-Hant-TW".
	languageCodePattern = regexp.MustCompile(`^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,3}$`)
)

const (
	maxImagePromptChars     = 10000
	maxAdaptationPhrases    = 100
	maxAdaptationPhraseLen  = 200
	maxRealtimeAudioMIMELen = 64
)

var errNotDataURL = errors.New(`expected a "data:<mime>;base64,<data>" URL`)

// parseImageDataURL decodes a base64 data URL and checks its MIME type
// against allowed. It replaces ad-hoc strings.Split(s, ",") parsing, which
// silently ignored malformed input.
func parseImageDataURL(s string, allowed map[string]bool) (mime string, data []byte, err error) {
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

// truncateRunes caps s at maxRunes characters without splitting a UTF-8
// sequence. The frontend enforces the same limits in UTF-16 code units, which
// are always >= the rune count, so frontend-accepted text is never cut.
func truncateRunes(s string, maxRunes int) string {
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

func validPresetName(s string) bool   { return presetNamePattern.MatchString(s) }
func validLanguageCode(s string) bool { return languageCodePattern.MatchString(s) }

// validRealtimeAudioMIME accepts the PCM formats the Live API takes for
// realtime input, e.g. "audio/pcm" or "audio/pcm;rate=16000".
func validRealtimeAudioMIME(s string) bool {
	if len(s) > maxRealtimeAudioMIMELen {
		return false
	}
	base, params, _ := strings.Cut(strings.ToLower(strings.TrimSpace(s)), ";")
	if base != "audio/pcm" {
		return false
	}
	return params == "" || parsePCMSampleRate(s) > 0
}

// inRange reports whether an optional float is within [lo, hi].
func inRange(v *float32, lo, hi float32) bool {
	return v == nil || (*v >= lo && *v <= hi)
}

// Accepted values for the client-supplied VAD sensitivity and ActivityHandling
// fields. These mirror the genai enums; the UNSPECIFIED variants are
// deliberately excluded, since "unspecified" is expressed by omitting the field.
var (
	validStartSensitivity = map[string]bool{
		string(genai.StartSensitivityHigh): true,
		string(genai.StartSensitivityLow):  true,
	}
	validEndSensitivity = map[string]bool{
		string(genai.EndSensitivityHigh): true,
		string(genai.EndSensitivityLow):  true,
	}
	validActivityHandling = map[string]bool{
		string(genai.ActivityHandlingStartOfActivityInterrupts): true,
		string(genai.ActivityHandlingNoInterruption):            true,
	}
)
