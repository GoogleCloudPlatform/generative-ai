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
	"fmt"
	"log/slog"
	"strings"

	"google.golang.org/genai"
)

// fallbackLiveModel is used when GEMINI_LIVE_MODEL is unset.
const fallbackLiveModel = "gemini-3.8-live"

const (
	maxGroundingContextChars  = 32000
	maxSystemInstructionChars = 32000
)

func capGroundingContext(s string) string {
	return truncateRunes(s, maxGroundingContextChars)
}

func capSystemInstruction(s string) string {
	return truncateRunes(s, maxSystemInstructionChars)
}

type liveMode string

const (
	liveModeAvatar liveMode = "avatar"
	liveModeAudio  liveMode = "audio"
)

// buildLiveConnectConfig translates the client's InitialConfig into the
// LiveConnectConfig sent to the Live API for an avatar session. It is shared by
// the /ws handler and the live smoke test so both exercise the exact same setup
// frame.
func buildLiveConnectConfig(initialConfig InitialConfig) (*genai.LiveConnectConfig, error) {
	return buildLiveConnectConfigForMode(initialConfig, liveModeAvatar)
}

// buildLiveConnectConfigForMode translates the client's InitialConfig into the
// LiveConnectConfig for either liveModeAvatar (/ws, VIDEO + AvatarConfig) or
// liveModeAudio (/ws/live, AUDIO + nil AvatarConfig). Only a broken avatar is
// an error; invalid optional values are logged and dropped.
func buildLiveConnectConfigForMode(initialConfig InitialConfig, mode liveMode) (*genai.LiveConnectConfig, error) {
	var avatarConfig *genai.AvatarConfig
	modality := genai.ModalityAudio
	if mode == liveModeAvatar {
		var err error
		if avatarConfig, err = buildAvatarConfig(initialConfig); err != nil {
			return nil, err
		}
		modality = genai.ModalityVideo
	}

	languageCode := resolveLanguageCode(initialConfig.LanguageCode)
	includeSearch := initialConfig.EnableGoogleSearch == nil || *initialConfig.EnableGoogleSearch
	includeToolCalling := initialConfig.EnableToolCalling != nil && *initialConfig.EnableToolCalling

	config := &genai.LiveConnectConfig{
		ResponseModalities: []genai.Modality{modality},
		SystemInstruction: &genai.Content{
			Parts: []*genai.Part{{Text: buildSystemInstruction(initialConfig, mode, includeToolCalling)}},
		},
		AvatarConfig: avatarConfig,
		SpeechConfig: &genai.SpeechConfig{
			VoiceConfig: &genai.VoiceConfig{
				PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{VoiceName: resolveVoiceName(initialConfig.VoiceName)},
			},
			LanguageCode: languageCode,
		},
		InputAudioTranscription: &genai.AudioTranscriptionConfig{
			LanguageCodes:     []string{languageCode},
			AdaptationPhrases: cleanAdaptationPhrases(initialConfig.AdaptationPhrases),
		},
		OutputAudioTranscription: &genai.AudioTranscriptionConfig{LanguageCodes: []string{languageCode}},
		Tools:                    buildTools(includeSearch, includeToolCalling),
	}
	applySampling(config, initialConfig)
	applyProactivity(config, initialConfig)
	config.ContextWindowCompression = buildContextWindowCompression(initialConfig)
	config.RealtimeInputConfig = buildRealtimeInputConfig(initialConfig)
	return config, nil
}

// buildAvatarConfig validates the avatar. VIDEO responses require an
// AvatarConfig, so a missing or broken avatar is a hard error here rather than
// a 1007 from the Live API later.
func buildAvatarConfig(initialConfig InitialConfig) (*genai.AvatarConfig, error) {
	switch initialConfig.AvatarType {
	case "preset":
		if !validPresetName(initialConfig.AvatarData) {
			return nil, fmt.Errorf("invalid preset avatar name %q", truncateRunes(initialConfig.AvatarData, maxLoggedValueRunes))
		}
		return &genai.AvatarConfig{AvatarName: initialConfig.AvatarData}, nil
	case "custom":
		mimeType, image, err := parseImageDataURL(initialConfig.AvatarData, avatarImageMIMETypes)
		if err != nil {
			return nil, fmt.Errorf("invalid custom avatar image: %w", err)
		}
		return &genai.AvatarConfig{
			CustomizedAvatar: &genai.CustomizedAvatar{ImageMIMEType: mimeType, ImageData: image},
		}, nil
	default:
		return nil, fmt.Errorf("unknown avatarType %q (want \"preset\" or \"custom\")", truncateRunes(initialConfig.AvatarType, maxLoggedValueRunes))
	}
}

// resolveLanguageCode returns a valid BCP-47-style code, defaulting to en-US.
func resolveLanguageCode(requested string) string {
	code := strings.TrimSpace(requested)
	if code != "" && !validLanguageCode(code) {
		slog.Warn("ignoring invalid languageCode", "value", truncateRunes(code, maxLoggedValueRunes))
		code = ""
	}
	if code == "" {
		return "en-US"
	}
	return code
}

// resolveVoiceName returns the requested prebuilt voice, or "" (server
// default) if it is malformed.
func resolveVoiceName(requested string) string {
	voice := strings.TrimSpace(requested)
	if voice != "" && !validPresetName(voice) {
		slog.Warn("ignoring invalid voiceName; using the server default voice", "value", truncateRunes(voice, maxLoggedValueRunes))
		return ""
	}
	return voice
}

// cleanAdaptationPhrases trims, caps and drops empty speech adaptation phrases.
func cleanAdaptationPhrases(phrases []string) []string {
	var cleaned []string
	for _, phrase := range phrases {
		if len(cleaned) == maxAdaptationPhrases {
			slog.Warn("ignoring extra adaptationPhrases", "max", maxAdaptationPhrases)
			break
		}
		if trimmed := truncateRunes(strings.TrimSpace(phrase), maxAdaptationPhraseLen); trimmed != "" {
			cleaned = append(cleaned, trimmed)
		}
	}
	return cleaned
}

// buildSystemInstruction combines the client's instruction (or the preset's
// default persona), grounding context, and the tool-calling hint.
func buildSystemInstruction(initialConfig InitialConfig, mode liveMode, includeToolCalling bool) string {
	instruction := capSystemInstruction(strings.TrimSpace(initialConfig.SystemInstruction))
	if instruction == "" && mode == liveModeAvatar && initialConfig.AvatarType == "preset" {
		instruction = defaultSystemInstructions[initialConfig.AvatarData]
	}
	if instruction == "" {
		instruction = "You are a helpful AI assistant."
	}
	if grounding := strings.TrimSpace(initialConfig.GroundingContext); grounding != "" {
		instruction += "\n\nUse the following reference material to answer questions when it's relevant:\n" + capGroundingContext(grounding)
	}
	if includeToolCalling {
		instruction += "\n\nYou have access to the `show_info_card` tool. When presenting structured summaries, key takeaways, step-by-step instructions, checklists, or reference facts, call `show_info_card` to display a visual card in the user's transcript panel while speaking naturally."
	}
	return instruction
}

func buildTools(includeSearch, includeToolCalling bool) []*genai.Tool {
	if !includeSearch && !includeToolCalling {
		return nil
	}
	tool := &genai.Tool{}
	if includeSearch {
		tool.GoogleSearch = &genai.GoogleSearch{}
	}
	if includeToolCalling {
		tool.FunctionDeclarations = builtInFunctionDeclarations()
	}
	return []*genai.Tool{tool}
}

// applySampling copies in-range sampling values. Out-of-range values are
// dropped (server default) rather than rejected by the Live API mid-connect.
func applySampling(config *genai.LiveConnectConfig, initialConfig InitialConfig) {
	if inRange(initialConfig.Temperature, 0, 2) {
		config.Temperature = initialConfig.Temperature
	} else {
		slog.Warn("ignoring out-of-range temperature (want 0..2)", "value", *initialConfig.Temperature)
	}
	if inRange(initialConfig.TopP, 0, 1) {
		config.TopP = initialConfig.TopP
	} else {
		slog.Warn("ignoring out-of-range topP (want 0..1)", "value", *initialConfig.TopP)
	}
	if inRange(initialConfig.TopK, 1, 1000) {
		config.TopK = initialConfig.TopK
	} else {
		slog.Warn("ignoring out-of-range topK (want 1..1000)", "value", *initialConfig.TopK)
	}
	if initialConfig.MaxOutputTokens > 0 {
		config.MaxOutputTokens = initialConfig.MaxOutputTokens
	}
}

func applyProactivity(config *genai.LiveConnectConfig, initialConfig InitialConfig) {
	if initialConfig.ProactiveAudio == nil || !*initialConfig.ProactiveAudio {
		return
	}
	if !supportsProactiveAudio(initialConfig.LiveModel) {
		slog.Warn("ignoring proactiveAudio: only supported on 3.8 and lite models", "model", initialConfig.LiveModel)
		return
	}
	proactive := true
	config.Proactivity = &genai.ProactivityConfig{ProactiveAudio: &proactive}
}

// buildContextWindowCompression enables sliding-window compression when the
// client asks for it or sets a trigger, unless it explicitly turned it off.
func buildContextWindowCompression(initialConfig InitialConfig) *genai.ContextWindowCompressionConfig {
	requested := initialConfig.ContextWindowCompression
	if requested != nil && !*requested {
		return nil
	}
	if (requested == nil || !*requested) && initialConfig.CompressionTriggerTokens <= 0 {
		return nil
	}
	compression := &genai.ContextWindowCompressionConfig{SlidingWindow: &genai.SlidingWindow{}}
	if initialConfig.CompressionTriggerTokens > 0 {
		trigger := initialConfig.CompressionTriggerTokens
		compression.TriggerTokens = &trigger
	}
	return compression
}

// buildRealtimeInputConfig returns VAD / ActivityHandling overrides, or nil
// when the client asked for none. Sending zero-valued fields is not the same
// as omitting them: an empty AutomaticActivityDetection would override the
// server defaults with nothing.
func buildRealtimeInputConfig(initialConfig InitialConfig) *genai.RealtimeInputConfig {
	var detection *genai.AutomaticActivityDetection
	if initialConfig.SilenceDurationMs > 0 || initialConfig.PrefixPaddingMs > 0 || initialConfig.StartOfSpeechSensitivity != "" || initialConfig.EndOfSpeechSensitivity != "" {
		detection = &genai.AutomaticActivityDetection{}
		if initialConfig.SilenceDurationMs > 0 {
			detection.SilenceDurationMs = &initialConfig.SilenceDurationMs
		}
		if initialConfig.PrefixPaddingMs > 0 {
			detection.PrefixPaddingMs = &initialConfig.PrefixPaddingMs
		}
		if v := initialConfig.StartOfSpeechSensitivity; v != "" {
			if validStartSensitivity[v] {
				detection.StartOfSpeechSensitivity = genai.StartSensitivity(v)
			} else {
				slog.Warn("ignoring unknown startOfSpeechSensitivity", "value", v)
			}
		}
		if v := initialConfig.EndOfSpeechSensitivity; v != "" {
			if validEndSensitivity[v] {
				detection.EndOfSpeechSensitivity = genai.EndSensitivity(v)
			} else {
				slog.Warn("ignoring unknown endOfSpeechSensitivity", "value", v)
			}
		}
	}

	var activityHandling genai.ActivityHandling
	if v := initialConfig.ActivityHandling; v != "" {
		if validActivityHandling[v] {
			activityHandling = genai.ActivityHandling(v)
		} else {
			slog.Warn("ignoring unknown activityHandling", "value", v)
		}
	}

	if detection == nil && activityHandling == "" {
		return nil
	}
	slog.Info("RealtimeInputConfig override",
		"silenceMs", initialConfig.SilenceDurationMs, "prefixMs", initialConfig.PrefixPaddingMs,
		"startSensitivity", initialConfig.StartOfSpeechSensitivity, "endSensitivity", initialConfig.EndOfSpeechSensitivity,
		"activityHandling", activityHandling)
	return &genai.RealtimeInputConfig{AutomaticActivityDetection: detection, ActivityHandling: activityHandling}
}

// supportsProactiveAudio reports whether the target Live model supports
// ProactivityConfig.ProactiveAudio without rejecting setup with 1007.
func supportsProactiveAudio(model string) bool {
	if strings.TrimSpace(model) == "" {
		model = fallbackLiveModel
	}
	return strings.Contains(model, "3.8") || strings.Contains(model, "lite")
}

// builtInFunctionDeclarations returns the interactive tools available to Gemini
// Live sessions when EnableToolCalling is enabled.
func builtInFunctionDeclarations() []*genai.FunctionDeclaration {
	return []*genai.FunctionDeclaration{
		{
			Name:        "show_info_card",
			Description: "Display a structured visual info card in the user's live transcript panel. Call this when sharing key takeaways, summaries, step-by-step instructions, checklists, or reference facts.",
			Parameters: &genai.Schema{
				Type: genai.TypeObject,
				Properties: map[string]*genai.Schema{
					"title": {
						Type:        genai.TypeString,
						Description: "Short, clear heading for the info card.",
					},
					"summary": {
						Type:        genai.TypeString,
						Description: "Concise body text or explanation to display on the card.",
					},
					"category": {
						Type:        genai.TypeString,
						Description: "Optional badge label such as Summary, Checklist, Architecture, Tip, or Reference.",
					},
					"items": {
						Type:        genai.TypeArray,
						Description: "Optional bullet points or key items to highlight on the card.",
						Items: &genai.Schema{
							Type: genai.TypeString,
						},
					},
				},
				Required: []string{"title", "summary"},
			},
		},
	}
}

// executeBuiltInTool executes a server-handled Live tool call and returns a
// structured response map suitable for genai.FunctionResponse.Response.
func executeBuiltInTool(name string, args map[string]any) map[string]any {
	switch name {
	case "show_info_card":
		title, _ := args["title"].(string)
		return map[string]any{
			"status":  "displayed",
			"title":   title,
			"message": "Info card is now visible to the user in the transcript panel.",
		}
	default:
		return map[string]any{
			"status": "unknown_tool",
			"error":  fmt.Sprintf("unrecognized tool %q", name),
		}
	}
}

// liveGreeting returns the line the avatar is prompted to say once setup completes.
// If the client supplied a custom WelcomeMessage override, it takes precedence.
func liveGreeting(initialConfig InitialConfig) string {
	return liveGreetingForMode(initialConfig, liveModeAvatar)
}

func liveGreetingForMode(initialConfig InitialConfig, mode liveMode) string {
	if custom := strings.TrimSpace(initialConfig.WelcomeMessage); custom != "" {
		return custom
	}
	if mode == liveModeAudio {
		return "Hello! I'm ready for our live conversation. What's on your mind?"
	}
	if initialConfig.AvatarType != "preset" {
		return "Hello! I am your custom avatar. I'm ready to assist you!"
	}
	if g, ok := defaultGreetings[initialConfig.AvatarData]; ok {
		return g
	}
	return "Hello, I'm your AI assistant. How can I help you?"
}

// greetingPrompt is the realtime text input that triggers the greeting turn.
func greetingPrompt(greeting string) string {
	return "Proactively introduce yourself now. Say exactly this: " + greeting
}

// parsePCMSampleRate extracts the numeric sample rate from a MIME type such as
// "audio/pcm;rate=24000", returning 0 when absent or malformed.
func parsePCMSampleRate(mime string) int {
	const marker = "rate="
	idx := strings.Index(mime, marker)
	if idx == -1 {
		return 0
	}
	rateStr := mime[idx+len(marker):]
	if end := strings.IndexAny(rateStr, ";, "); end != -1 {
		rateStr = rateStr[:end]
	}
	var rate int
	if _, err := fmt.Sscanf(rateStr, "%d", &rate); err != nil {
		return 0
	}
	return rate
}
