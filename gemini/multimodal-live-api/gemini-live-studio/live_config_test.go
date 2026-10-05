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
	"testing"

	"google.golang.org/genai"
)

func TestBuildLiveConnectConfig_Preset(t *testing.T) {
	cfg, err := buildLiveConnectConfig(InitialConfig{AvatarType: "preset", AvatarData: "Ben", VoiceName: "Puck"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// The Live API rejects AUDIO+VIDEO together; VIDEO alone must be requested.
	if len(cfg.ResponseModalities) != 1 || cfg.ResponseModalities[0] != genai.ModalityVideo {
		t.Errorf("ResponseModalities = %v, want [VIDEO]", cfg.ResponseModalities)
	}
	if cfg.AvatarConfig == nil || cfg.AvatarConfig.AvatarName != "Ben" {
		t.Errorf("AvatarConfig = %+v, want preset Ben", cfg.AvatarConfig)
	}
	if got := cfg.SystemInstruction.Parts[0].Text; got != defaultSystemInstructions["Ben"] {
		t.Errorf("SystemInstruction = %q, want Ben's default", got)
	}
	if got := cfg.SpeechConfig.VoiceConfig.PrebuiltVoiceConfig.VoiceName; got != "Puck" {
		t.Errorf("VoiceName = %q, want Puck", got)
	}
	if cfg.SpeechConfig.LanguageCode != "en-US" {
		t.Errorf("LanguageCode = %q, want en-US default", cfg.SpeechConfig.LanguageCode)
	}
	for name, tc := range map[string]*genai.AudioTranscriptionConfig{
		"input":  cfg.InputAudioTranscription,
		"output": cfg.OutputAudioTranscription,
	} {
		if tc == nil || len(tc.LanguageCodes) != 1 || tc.LanguageCodes[0] != "en-US" {
			t.Errorf("%s transcription = %+v, want LanguageCodes [en-US]", name, tc)
		}
	}
	if len(cfg.Tools) != 1 || cfg.Tools[0].GoogleSearch == nil {
		t.Errorf("Tools = %+v, want GoogleSearch only", cfg.Tools)
	}
	if cfg.RealtimeInputConfig != nil {
		t.Errorf("RealtimeInputConfig should be nil when no VAD overrides are given")
	}
}

func TestBuildLiveConnectConfig_CustomAvatar(t *testing.T) {
	img := []byte{0x89, 'P', 'N', 'G'}
	data := "data:image/png;base64," + base64.StdEncoding.EncodeToString(img)

	cfg, err := buildLiveConnectConfig(InitialConfig{AvatarType: "custom", AvatarData: data, LanguageCode: "fr-FR"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	ca := cfg.AvatarConfig.CustomizedAvatar
	if ca == nil || ca.ImageMIMEType != "image/png" || !bytes.Equal(ca.ImageData, img) {
		t.Errorf("CustomizedAvatar = %+v, want image/png with decoded bytes", ca)
	}
	if got := cfg.SystemInstruction.Parts[0].Text; got != "You are a helpful AI assistant." {
		t.Errorf("SystemInstruction = %q, want generic fallback", got)
	}
	if cfg.SpeechConfig.LanguageCode != "fr-FR" {
		t.Errorf("LanguageCode = %q, want fr-FR", cfg.SpeechConfig.LanguageCode)
	}
}

func TestBuildLiveConnectConfig_InvalidAvatarData(t *testing.T) {
	if _, err := buildLiveConnectConfig(InitialConfig{AvatarType: "custom", AvatarData: "data:image/png;base64,!!!"}); err == nil {
		t.Fatal("expected error for invalid base64 avatar data")
	}
}

func TestBuildLiveConnectConfig_VAD(t *testing.T) {
	cfg, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:               "preset",
		AvatarData:               "Ben",
		SilenceDurationMs:        800,
		StartOfSpeechSensitivity: string(genai.StartSensitivityLow),
		EndOfSpeechSensitivity:   "BOGUS",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.RealtimeInputConfig == nil || cfg.RealtimeInputConfig.AutomaticActivityDetection == nil {
		t.Fatal("expected RealtimeInputConfig with AutomaticActivityDetection")
	}
	aad := cfg.RealtimeInputConfig.AutomaticActivityDetection
	if aad.SilenceDurationMs == nil || *aad.SilenceDurationMs != 800 {
		t.Errorf("SilenceDurationMs = %v, want 800", aad.SilenceDurationMs)
	}
	if aad.PrefixPaddingMs != nil {
		t.Errorf("PrefixPaddingMs should be omitted, got %v", *aad.PrefixPaddingMs)
	}
	if aad.StartOfSpeechSensitivity != genai.StartSensitivityLow {
		t.Errorf("StartOfSpeechSensitivity = %q, want LOW", aad.StartOfSpeechSensitivity)
	}
	if aad.EndOfSpeechSensitivity != "" {
		t.Errorf("unknown EndOfSpeechSensitivity should be dropped, got %q", aad.EndOfSpeechSensitivity)
	}
}

func TestBuildLiveConnectConfig_GroundingContext(t *testing.T) {
	cfg, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:        "preset",
		AvatarData:        "Ben",
		SystemInstruction: "You are a technical reviewer.",
		GroundingContext:  "Project code: APOLLO-99",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	got := cfg.SystemInstruction.Parts[0].Text
	want := "You are a technical reviewer.\n\nUse the following reference material to answer questions when it's relevant:\nProject code: APOLLO-99"
	if got != want {
		t.Errorf("SystemInstruction = %q, want %q", got, want)
	}
}

func TestLiveGreeting(t *testing.T) {
	if got := liveGreeting(InitialConfig{AvatarType: "preset", AvatarData: "Ben"}); got != defaultGreetings["Ben"] {
		t.Errorf("preset greeting = %q", got)
	}
	if got := liveGreeting(InitialConfig{AvatarType: "preset", AvatarData: "Ben", WelcomeMessage: "  Welcome aboard!  "}); got != "Welcome aboard!" {
		t.Errorf("custom welcome override = %q, want %q", got, "Welcome aboard!")
	}
	if got := liveGreeting(InitialConfig{AvatarType: "preset", AvatarData: "Unknown"}); got != "Hello, I'm your AI assistant. How can I help you?" {
		t.Errorf("unknown preset greeting = %q", got)
	}
	if got := liveGreeting(InitialConfig{AvatarType: "custom"}); got != "Hello! I am your custom avatar. I'm ready to assist you!" {
		t.Errorf("custom greeting = %q", got)
	}
	if got := liveGreeting(InitialConfig{AvatarType: "custom", WelcomeMessage: "Greetings from your custom persona!"}); got != "Greetings from your custom persona!" {
		t.Errorf("custom avatar with custom welcome = %q", got)
	}
	if got := liveGreetingForMode(InitialConfig{}, liveModeAudio); got != "Hello! I'm ready for our live conversation. What's on your mind?" {
		t.Errorf("audio mode default greeting = %q", got)
	}
	if got := liveGreetingForMode(InitialConfig{WelcomeMessage: "Custom audio greeting"}, liveModeAudio); got != "Custom audio greeting" {
		t.Errorf("audio mode custom greeting = %q", got)
	}
}

func TestBuildLiveConnectConfigForMode_Audio(t *testing.T) {
	cfg, err := buildLiveConnectConfigForMode(InitialConfig{
		VoiceName:        "Aoede",
		GroundingContext: "Live Audio reference notes",
	}, liveModeAudio)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(cfg.ResponseModalities) != 1 || cfg.ResponseModalities[0] != genai.ModalityAudio {
		t.Errorf("ResponseModalities = %v, want [AUDIO]", cfg.ResponseModalities)
	}
	if cfg.AvatarConfig != nil {
		t.Errorf("AvatarConfig = %+v, want nil in liveModeAudio", cfg.AvatarConfig)
	}
	if len(cfg.Tools) != 1 || cfg.Tools[0].GoogleSearch == nil {
		t.Errorf("Tools = %+v, want GoogleSearch enabled by default in liveModeAudio", cfg.Tools)
	}

	falseVal := false
	cfgNoSearch, err := buildLiveConnectConfigForMode(InitialConfig{
		VoiceName:          "Aoede",
		EnableGoogleSearch: &falseVal,
	}, liveModeAudio)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgNoSearch.Tools != nil {
		t.Errorf("Tools = %+v, want nil when EnableGoogleSearch is false in liveModeAudio", cfgNoSearch.Tools)
	}
}

func TestParsePCMSampleRate(t *testing.T) {
	tests := []struct {
		mime string
		want int
	}{
		{"audio/pcm;rate=24000", 24000},
		{"audio/pcm; rate=16000", 16000},
		{"audio/pcm;rate=24000;extra=foo", 24000},
		{"audio/pcm", 0},
		{"video/mp4", 0},
		{"", 0},
		{"audio/pcm;rate=notanumber", 0},
	}
	for _, tt := range tests {
		if got := parsePCMSampleRate(tt.mime); got != tt.want {
			t.Errorf("parsePCMSampleRate(%q) = %d, want %d", tt.mime, got, tt.want)
		}
	}
}

func TestBuildLiveConnectConfig_ProactiveAudioAndCompression(t *testing.T) {
	trueVal := true
	falseVal := false

	cfg, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:               "preset",
		AvatarData:               "Ben",
		LiveModel:                "gemini-3.8-live",
		ProactiveAudio:           &trueVal,
		ContextWindowCompression: &trueVal,
		CompressionTriggerTokens: 16000,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Proactivity == nil || cfg.Proactivity.ProactiveAudio == nil || !*cfg.Proactivity.ProactiveAudio {
		t.Errorf("Proactivity = %+v, want ProactiveAudio=true for gemini-3.8-live", cfg.Proactivity)
	}
	if cfg.ContextWindowCompression == nil || cfg.ContextWindowCompression.SlidingWindow == nil {
		t.Fatalf("ContextWindowCompression = %+v, want SlidingWindow", cfg.ContextWindowCompression)
	}
	if cfg.ContextWindowCompression.TriggerTokens == nil || *cfg.ContextWindowCompression.TriggerTokens != 16000 {
		t.Errorf("TriggerTokens = %v, want 16000", cfg.ContextWindowCompression.TriggerTokens)
	}

	// Non-3.8 / non-lite models must ignore ProactiveAudio to avoid 1007.
	cfgUnsupported, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:               "preset",
		AvatarData:               "Ben",
		LiveModel:                "gemini-3.5-flash-live-preview",
		ProactiveAudio:           &trueVal,
		ContextWindowCompression: &falseVal,
		CompressionTriggerTokens: 16000,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgUnsupported.Proactivity != nil {
		t.Errorf("Proactivity = %+v, want nil for gemini-3.5-flash-live-preview", cfgUnsupported.Proactivity)
	}
	if cfgUnsupported.ContextWindowCompression != nil {
		t.Errorf("ContextWindowCompression = %+v, want nil when explicitly false", cfgUnsupported.ContextWindowCompression)
	}
}

func TestBuildLiveConnectConfig_AdaptationActivityAndGenerationParams(t *testing.T) {
	temp := float32(0.7)
	topP := float32(0.9)
	topK := float32(40)

	cfg, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:        "preset",
		AvatarData:        "Ben",
		AdaptationPhrases: []string{"  Kubernetes ", "", "gRPC", "   "},
		ActivityHandling:  string(genai.ActivityHandlingNoInterruption),
		Temperature:       &temp,
		TopP:              &topP,
		TopK:              &topK,
		MaxOutputTokens:   1024,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	gotPhrases := cfg.InputAudioTranscription.AdaptationPhrases
	if len(gotPhrases) != 2 || gotPhrases[0] != "Kubernetes" || gotPhrases[1] != "gRPC" {
		t.Errorf("AdaptationPhrases = %v, want [Kubernetes gRPC]", gotPhrases)
	}
	if cfg.RealtimeInputConfig == nil {
		t.Fatal("expected RealtimeInputConfig when ActivityHandling is set")
	}
	if cfg.RealtimeInputConfig.AutomaticActivityDetection != nil {
		t.Errorf("AutomaticActivityDetection = %+v, want nil when only ActivityHandling is set", cfg.RealtimeInputConfig.AutomaticActivityDetection)
	}
	if cfg.RealtimeInputConfig.ActivityHandling != genai.ActivityHandlingNoInterruption {
		t.Errorf("ActivityHandling = %q, want NO_INTERRUPTION", cfg.RealtimeInputConfig.ActivityHandling)
	}
	if cfg.Temperature == nil || *cfg.Temperature != temp {
		t.Errorf("Temperature = %v, want %v", cfg.Temperature, temp)
	}
	if cfg.TopP == nil || *cfg.TopP != topP {
		t.Errorf("TopP = %v, want %v", cfg.TopP, topP)
	}
	if cfg.TopK == nil || *cfg.TopK != topK {
		t.Errorf("TopK = %v, want %v", cfg.TopK, topK)
	}
	if cfg.MaxOutputTokens != 1024 {
		t.Errorf("MaxOutputTokens = %d, want 1024", cfg.MaxOutputTokens)
	}
}

func TestBuildLiveConnectConfig_ToolCallingAndSearchToggle(t *testing.T) {
	trueVal := true
	falseVal := false

	cfg, err := buildLiveConnectConfig(InitialConfig{
		AvatarType:         "preset",
		AvatarData:         "Ben",
		EnableGoogleSearch: &falseVal,
		EnableToolCalling:  &trueVal,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(cfg.Tools) != 1 {
		t.Fatalf("len(Tools) = %d, want 1", len(cfg.Tools))
	}
	if cfg.Tools[0].GoogleSearch != nil {
		t.Errorf("GoogleSearch = %+v, want nil when EnableGoogleSearch=false", cfg.Tools[0].GoogleSearch)
	}
	if len(cfg.Tools[0].FunctionDeclarations) != 1 || cfg.Tools[0].FunctionDeclarations[0].Name != "show_info_card" {
		t.Errorf("FunctionDeclarations = %+v, want [show_info_card]", cfg.Tools[0].FunctionDeclarations)
	}

	res := executeBuiltInTool("show_info_card", map[string]any{
		"title":   "Gemini 3.8 Live",
		"summary": "Low-latency native audio and video streaming.",
	})
	if res["status"] != "displayed" || res["title"] != "Gemini 3.8 Live" {
		t.Errorf("executeBuiltInTool(show_info_card) = %+v", res)
	}
}
