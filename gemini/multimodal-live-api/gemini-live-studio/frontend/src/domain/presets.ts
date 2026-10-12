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

import type { AppSettings } from '../store';

export type UploadTransformMode = 'avatar' | 'none' | 'remove-bg';

export const MAX_GROUNDING_CONTEXT_CHARS = 32000;
export const MAX_SYSTEM_INSTRUCTION_CHARS = 32000;

export interface LiveSessionTuningOptions {
  welcomeMessage?: string;
  systemInstruction?: string;
  groundingContext?: string;
  liveModel?: string;
  liveLocation?: string;
  enableGoogleSearch?: boolean;
  enableToolCalling?: boolean;
  proactiveAudio?: boolean;
  contextWindowCompression?: boolean;
  compressionTriggerTokens?: number;
  adaptationPhrases?: string[];
  temperature?: number;
  topP?: number;
  topK?: number;
  maxOutputTokens?: number;
  // VAD & Barge-in tuning. Omitted when unset so the server keeps its defaults.
  startOfSpeechSensitivity?: string;
  endOfSpeechSensitivity?: string;
  silenceDurationMs?: number;
  prefixPaddingMs?: number;
  activityHandling?: string;
}

export interface AvatarConfigEvent extends LiveSessionTuningOptions {
  avatarType: 'preset' | 'custom';
  avatarData: string;
  voiceName: string;
}

export interface LiveConfigEvent extends LiveSessionTuningOptions {
  voiceName: string;
}

export function buildSessionTuningPayload(
  settings: AppSettings,
): LiveSessionTuningOptions {
  const vad = settings.vadSettings ?? {};
  const gen = settings.generationSettings ?? {};
  const ms = settings.modelSettings ?? {};
  return {
    liveModel: ms.liveModel || undefined,
    liveLocation: ms.liveLocation || undefined,
    startOfSpeechSensitivity: vad.startOfSpeechSensitivity || undefined,
    endOfSpeechSensitivity: vad.endOfSpeechSensitivity || undefined,
    silenceDurationMs: vad.silenceDurationMs || undefined,
    prefixPaddingMs: vad.prefixPaddingMs || undefined,
    activityHandling: vad.activityHandling || undefined,
    proactiveAudio: gen.proactiveAudio ? true : undefined,
    contextWindowCompression:
      gen.contextWindowCompression !== undefined
        ? gen.contextWindowCompression
        : undefined,
    compressionTriggerTokens: gen.compressionTriggerTokens || undefined,
    adaptationPhrases:
      gen.adaptationPhrases && gen.adaptationPhrases.length > 0
        ? gen.adaptationPhrases
        : undefined,
    temperature: gen.temperature !== undefined ? gen.temperature : undefined,
    topP: gen.topP !== undefined ? gen.topP : undefined,
    topK: gen.topK !== undefined ? gen.topK : undefined,
    maxOutputTokens: gen.maxOutputTokens || undefined,
  };
}

export interface VoiceOption {
  name: string;
  tone: string;
}

export const VOICES: readonly VoiceOption[] = [
  { name: 'Puck', tone: 'Upbeat' },
  { name: 'Aoede', tone: 'Breezy' },
  { name: 'Charon', tone: 'Informative' },
  { name: 'Kore', tone: 'Firm' },
  { name: 'Fenrir', tone: 'Excitable' },
  { name: 'Zephyr', tone: 'Bright' },
  { name: 'Orus', tone: 'Firm' },
  { name: 'Autonoe', tone: 'Bright' },
  { name: 'Umbriel', tone: 'Easy-going' },
  { name: 'Erinome', tone: 'Clear' },
  { name: 'Laomedeia', tone: 'Upbeat' },
  { name: 'Schedar', tone: 'Even' },
  { name: 'Achird', tone: 'Friendly' },
  { name: 'Sadachbia', tone: 'Lively' },
  { name: 'Enceladus', tone: 'Breathy' },
  { name: 'Algieba', tone: 'Smooth' },
  { name: 'Algenib', tone: 'Gravelly' },
  { name: 'Achernar', tone: 'Soft' },
  { name: 'Gacrux', tone: 'Mature' },
  { name: 'Zubenelgenubi', tone: 'Casual' },
  { name: 'Sadaltager', tone: 'Knowledgeable' },
  { name: 'Leda', tone: 'Youthful' },
  { name: 'Callirrhoe', tone: 'Easy-going' },
  { name: 'Iapetus', tone: 'Clear' },
  { name: 'Despina', tone: 'Smooth' },
  { name: 'Rasalgethi', tone: 'Informative' },
  { name: 'Alnilam', tone: 'Firm' },
  { name: 'Pulcherrima', tone: 'Forward' },
  { name: 'Vindemiatrix', tone: 'Gentle' },
  { name: 'Sulafat', tone: 'Warm' },
].sort((a, b) => a.name.localeCompare(b.name));

export const VOICE_SELECT_OPTIONS: readonly {
  value: string;
  label: string;
}[] = VOICES.map((v) => ({
  value: v.name,
  label: `${v.name} \u2014 ${v.tone}`,
}));

export const PRESETS = [
  'Jay',
  'Paul',
  'Sam',
  'Ingrid',
  'Kira',
  'Vera',
  'Ben',
  'Kai',
  'Leo',
  'Carmen',
  'Piper',
] as const;

export type PresetAvatarName = (typeof PRESETS)[number];

export const PRESET_VOICES: Record<string, string> = {
  Jay: 'Puck',
  Paul: 'Charon',
  Sam: 'Schedar',
  Ingrid: 'Kore',
  Kira: 'Aoede',
  Vera: 'Erinome',
  Ben: 'Puck',
  Kai: 'Fenrir',
  Leo: 'Orus',
  Carmen: 'Laomedeia',
  Piper: 'Autonoe',
};

export const DEFAULT_GREETINGS: Record<string, string> = {
  Jay: "Hey there! I'm Jay. Ready to get to work?",
  Paul: "Hello, I'm Paul. How can I assist you today?",
  Sam: "Hi, Sam here! What's on your mind?",
  Ingrid: 'Good day. I am Ingrid. How may I help you?',
  Kira: "Hi! I'm Kira. It's great to meet you.",
  Vera: 'Hello, Vera speaking. What can we accomplish together?',
  Ben: "Hey! I'm Ben. What's up?",
  Kai: "Yo, I'm Kai! Let's do this.",
  Leo: 'Greetings! Leo here. What are we exploring today?',
  Carmen: "Hiya, I'm Carmen! Let's chat.",
  Piper: "Hello! Piper here. I'm ready when you are!",
};

export const DEFAULT_SYSTEM_INSTRUCTIONS: Record<string, string> = {
  Jay: 'You are Jay, a professional and highly efficient assistant. Your tone is direct, capable, and ready to get to work.',
  Paul: 'You are Paul, a formal and deeply knowledgeable AI assistant. You speak with polite precision and focus on providing accurate assistance.',
  Sam: "You are Sam, a friendly, curious, and approachable AI. You speak conversationally and always show an interest in the user's thoughts.",
  Ingrid:
    'Good day. You are Ingrid, a sophisticated and calm AI. Your responses are well-structured, polite, and emphasize clarity.',
  Kira: 'You are Kira, a welcoming and warm AI assistant. You use a gentle, friendly tone and strive to make the user feel comfortable.',
  Vera: 'You are Vera, a collaborative and professional AI. You focus on teamwork and accomplishing goals efficiently.',
  Ben: 'You are Ben, a casual, upbeat, and very friendly AI. Your language is colloquial, relaxed, and highly enthusiastic.',
  Kai: "You are Kai, an energetic and enthusiastic AI. You use a lot of exclamations, modern slang, and always show a 'can-do' attitude.",
  Leo: 'You are Leo, an inquisitive and exploratory AI. You love discussing new ideas, brainstorming, and asking thoughtful follow-up questions.',
  Carmen:
    'You are Carmen, a chatty and lively AI assistant. Your responses are full of energy, personable, and expressive.',
  Piper:
    'You are Piper, an eager and helpful AI. You are always ready to assist and speak with a bright, motivated tone.',
};
