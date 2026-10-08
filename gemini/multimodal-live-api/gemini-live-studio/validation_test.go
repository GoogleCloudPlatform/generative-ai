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
	"bytes"
	"encoding/base64"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
	"unicode/utf8"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

var pngDataURL = "data:image/png;base64," + base64.StdEncoding.EncodeToString([]byte("\x89PNG fake"))

func TestParseImageDataURL(t *testing.T) {
	cases := []struct {
		name, in, wantMIME string
		wantErr            bool
	}{
		{"png", pngDataURL, "image/png", false},
		{"jpeg uppercase mime", "data:IMAGE/JPEG;base64,AAEC", "image/jpeg", false},
		{"no comma (old code silently ignored this)", "data:image/png;base64AAEC", "", true},
		{"not a data url", "AAEC", "", true},
		{"missing base64 marker", "data:image/png,AAEC", "", true},
		{"webp rejected", "data:image/webp;base64,AAEC", "", true},
		{"bad base64", "data:image/png;base64,!!!", "", true},
		{"empty payload", "data:image/png;base64,", "", true},
		{"comma inside payload is not split", "data:image/png;base64,AA,EC", "", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			mime, data, err := parseImageDataURL(tc.in, avatarImageMIMETypes)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if !tc.wantErr && (mime != tc.wantMIME || len(data) == 0) {
				t.Fatalf("got mime=%q len=%d", mime, len(data))
			}
		})
	}
}

func TestTruncateRunes_KeepsUTF8Valid(t *testing.T) {
	s := strings.Repeat("é", 10) // 2 bytes per rune
	got := truncateRunes(s, 3)
	if got != strings.Repeat("é", 3) || !utf8.ValidString(got) {
		t.Fatalf("truncateRunes = %q", got)
	}
	if truncateRunes("abc", 5) != "abc" {
		t.Fatal("short strings must be unchanged")
	}
	// The old byte slice split a multi-byte rune at the 32k boundary.
	long := strings.Repeat("a", maxSystemInstructionChars-1) + strings.Repeat("😀", 5)
	if c := capSystemInstruction(long); !utf8.ValidString(c) || utf8.RuneCountInString(c) != maxSystemInstructionChars {
		t.Fatalf("capSystemInstruction produced invalid or wrong-length output (%d runes)", utf8.RuneCountInString(c))
	}
}

func TestBuildLiveConnectConfig_AvatarValidation(t *testing.T) {
	cases := []struct {
		name    string
		cfg     InitialConfig
		mode    liveMode
		wantErr bool
	}{
		{"preset ok", InitialConfig{AvatarType: "preset", AvatarData: "Kira"}, liveModeAvatar, false},
		{"custom ok", InitialConfig{AvatarType: "custom", AvatarData: pngDataURL}, liveModeAvatar, false},
		{"custom without comma", InitialConfig{AvatarType: "custom", AvatarData: "data:image/png;base64"}, liveModeAvatar, true},
		{"custom empty", InitialConfig{AvatarType: "custom"}, liveModeAvatar, true},
		{"custom webp", InitialConfig{AvatarType: "custom", AvatarData: "data:image/webp;base64,AAEC"}, liveModeAvatar, true},
		{"unknown avatarType", InitialConfig{AvatarType: "url", AvatarData: pngDataURL}, liveModeAvatar, true},
		{"empty avatarType", InitialConfig{AvatarData: "Kira"}, liveModeAvatar, true},
		{"preset empty name", InitialConfig{AvatarType: "preset"}, liveModeAvatar, true},
		{"preset junk name", InitialConfig{AvatarType: "preset", AvatarData: "../../etc"}, liveModeAvatar, true},
		{"audio mode ignores avatar", InitialConfig{AvatarType: "whatever"}, liveModeAudio, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := buildLiveConnectConfigForMode(tc.cfg, tc.mode)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if err == nil && tc.mode == liveModeAvatar && cfg.AvatarConfig == nil {
				t.Fatal("VIDEO session built without AvatarConfig")
			}
		})
	}
}

func TestBuildLiveConnectConfig_DropsInvalidOptionalValues(t *testing.T) {
	f := func(v float32) *float32 { return &v }
	phrases := make([]string, maxAdaptationPhrases+5)
	for i := range phrases {
		phrases[i] = strings.Repeat("x", maxAdaptationPhraseLen+10)
	}
	cfg, err := buildLiveConnectConfigForMode(InitialConfig{
		AvatarType:        "preset",
		AvatarData:        "Kira",
		LanguageCode:      "en_US; DROP",
		VoiceName:         "Kore\n",
		Temperature:       f(5),
		TopP:              f(-0.1),
		TopK:              f(0),
		AdaptationPhrases: phrases,
	}, liveModeAvatar)
	if err != nil {
		t.Fatalf("optional values must not fail setup: %v", err)
	}
	if got := cfg.SpeechConfig.LanguageCode; got != "en-US" {
		t.Errorf("languageCode = %q, want fallback en-US", got)
	}
	if got := cfg.SpeechConfig.VoiceConfig.PrebuiltVoiceConfig.VoiceName; got != "Kore" {
		t.Errorf("voiceName = %q, want trimmed Kore", got)
	}
	if cfg.Temperature != nil || cfg.TopP != nil || cfg.TopK != nil {
		t.Errorf("out-of-range sampling values forwarded: temp=%v topP=%v topK=%v", cfg.Temperature, cfg.TopP, cfg.TopK)
	}
	ap := cfg.InputAudioTranscription.AdaptationPhrases
	if len(ap) != maxAdaptationPhrases || utf8.RuneCountInString(ap[0]) != maxAdaptationPhraseLen {
		t.Errorf("adaptation phrases not capped: n=%d len0=%d", len(ap), utf8.RuneCountInString(ap[0]))
	}

	cfg, _ = buildLiveConnectConfigForMode(InitialConfig{AvatarType: "preset", AvatarData: "Kira", LanguageCode: "es-419", VoiceName: "bad voice!", Temperature: f(0.7)}, liveModeAvatar)
	if cfg.SpeechConfig.LanguageCode != "es-419" || cfg.Temperature == nil {
		t.Error("valid values must be kept")
	}
	if cfg.SpeechConfig.VoiceConfig.PrebuiltVoiceConfig.VoiceName != "" {
		t.Error("invalid voice name must fall back to the server default")
	}
}

func TestValidRealtimeAudioMIME(t *testing.T) {
	for in, want := range map[string]bool{
		"audio/pcm;rate=16000": true,
		"audio/pcm":            true,
		"AUDIO/PCM;rate=24000": true,
		"audio/pcm;rate=abc":   false,
		"audio/wav":            false,
		"":                     false,
		"audio/pcm;rate=16000" + strings.Repeat(" ", 100): false,
	} {
		if got := validRealtimeAudioMIME(in); got != want {
			t.Errorf("validRealtimeAudioMIME(%q) = %v, want %v", in, got, want)
		}
	}
}

func TestGenerateAvatarHandler_RejectsBadReferenceImage(t *testing.T) {
	h := generateAvatarHandler(newClientManager("test-project", ""), "gemini-3.1-flash-image", "global")
	for name, body := range map[string]string{
		"no comma":     `{"prompt":"x","image":"data:image/png;base64AAAA"}`,
		"bad base64":   `{"prompt":"x","image":"data:image/png;base64,!!!"}`,
		"webp":         `{"prompt":"x","image":"data:image/webp;base64,AAEC"}`,
		"long prompt":  `{"prompt":"` + strings.Repeat("p", maxImagePromptChars+1) + `"}`,
		"empty fields": `{}`,
	} {
		t.Run(name, func(t *testing.T) {
			w := httptest.NewRecorder()
			h(w, httptest.NewRequest(http.MethodPost, "/api/generate-avatar", bytes.NewBufferString(body)))
			if w.Code != http.StatusBadRequest {
				t.Fatalf("code=%d body=%q, want 400", w.Code, w.Body.String())
			}
		})
	}
}

func TestLiveSessionHandler_InvalidAvatarClosesWith1007(t *testing.T) {
	connector := &mockLiveConnector{session: newMockLiveSession()}
	srv := httptest.NewServer(liveSessionHandlerForMode(liveModeAvatar, connector, "gemini-3.8-live", "us-central1"))
	defer srv.Close()
	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(srv.URL, "http"), nil)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer func() { _ = conn.Close() }()
	_ = conn.WriteJSON(InitialConfig{AvatarType: "custom", AvatarData: "not-a-data-url"})
	_, _, err = conn.ReadMessage()
	if !websocket.IsCloseError(err, websocket.CloseInvalidFramePayloadData) {
		t.Fatalf("got %v, want close 1007", err)
	}
	if connector.gotModel != "" {
		t.Fatal("Live API was dialed with an invalid avatar")
	}
}

func TestLiveSessionHandler_DropsUnsupportedMediaMIME(t *testing.T) {
	h := newTeardownHarness(t)
	data := base64.StdEncoding.EncodeToString([]byte("x"))
	for _, m := range []map[string]string{
		{"type": "audio", "data": data, "mimeType": "audio/wav"},
		{"type": "video", "data": data, "mimeType": "image/webp"},
		{"type": "audio", "data": data, "mimeType": "audio/pcm;rate=16000"},
		{"type": "text", "data": "done"},
	} {
		if err := h.conn.WriteJSON(m); err != nil {
			t.Fatalf("write: %v", err)
		}
	}
	waitForText(t, h.session, "done")
	h.session.mu.Lock()
	defer h.session.mu.Unlock()
	var audio int
	for _, c := range h.session.realtimeCalls {
		if c.Video != nil {
			t.Fatal("webp video frame was forwarded")
		}
		if c.Audio != nil {
			audio++
			if c.Audio.MIMEType != "audio/pcm;rate=16000" {
				t.Fatalf("forwarded audio mime %q", c.Audio.MIMEType)
			}
		}
	}
	if audio != 1 {
		t.Fatalf("forwarded %d audio chunks, want 1", audio)
	}
}

func waitForText(t *testing.T, s *mockLiveSession, text string) {
	t.Helper()
	for i := 0; i < 400; i++ {
		s.mu.Lock()
		calls := append([]genai.LiveSendRealtimeInputParameters(nil), s.realtimeCalls...)
		s.mu.Unlock()
		for _, c := range calls {
			if c.Text == text {
				return
			}
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatalf("text %q never reached the session", text)
}
