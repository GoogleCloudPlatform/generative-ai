/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import type { GaTheme } from './theme/tokens';

export interface AvatarSettings {
  voiceName: string;
  welcomeMessage: string;
  systemInstruction: string;
}

export interface ModelSettings {
  liveModel?: string;
  liveLocation?: string;
  imageModel?: string;
}

/**
 * Voice Activity Detection tuning, mapped onto the Live API's
 * RealtimeInputConfig.AutomaticActivityDetection.
 *
 * Every field is optional and omitted from the wire when unset, so an
 * untouched config leaves the server on its own VAD defaults. Sending
 * zero-valued fields is not equivalent to omitting them.
 */
export interface VadSettings {
  /** How eagerly the model decides speech has started. */
  startOfSpeechSensitivity?: 'START_SENSITIVITY_HIGH' | 'START_SENSITIVITY_LOW';
  /** How eagerly the model decides speech has ended. */
  endOfSpeechSensitivity?: 'END_SENSITIVITY_HIGH' | 'END_SENSITIVITY_LOW';
  /** Silence required before the model treats your turn as finished (ms). */
  silenceDurationMs?: number;
  /** Audio retained from before speech onset, so leading words aren't clipped (ms). */
  prefixPaddingMs?: number;
  /** Whether user speech interrupts an active model turn (barge-in) or waits. */
  activityHandling?: 'START_OF_ACTIVITY_INTERRUPTS' | 'NO_INTERRUPTION';
}

export interface GenerationSettings {
  temperature?: number;
  topP?: number;
  topK?: number;
  maxOutputTokens?: number;
  proactiveAudio?: boolean;
  contextWindowCompression?: boolean;
  compressionTriggerTokens?: number;
  adaptationPhrases?: string[];
}

export interface AppSettings {
  uiVisibility: {
    showPresets: boolean;
    showUpload: boolean;
    showGenerate: boolean;
  };
  modelSettings: ModelSettings;
  vadSettings: VadSettings;
  generationSettings: GenerationSettings;
  avatarMappings: Record<string, AvatarSettings>;
  defaultAvatar: string;
  /** Colour theme applied to <html data-theme>. */
  theme: GaTheme;
}

function isTheme(v: unknown): v is GaTheme {
  return v === 'light' || v === 'dark' || v === 'system';
}

const DEFAULT_SETTINGS: AppSettings = {
  uiVisibility: {
    showPresets: true,
    showUpload: false,
    showGenerate: false,
  },
  modelSettings: {
    liveModel: '',
    liveLocation: '',
    imageModel: '',
  },
  // Empty by default: no VAD fields are sent, so the server uses its defaults.
  vadSettings: {},
  generationSettings: {
    contextWindowCompression: true,
  },
  avatarMappings: {},
  defaultAvatar: 'Ben',
  theme: 'light',
};

function cloneDefaultSettings(): AppSettings {
  return {
    uiVisibility: { ...DEFAULT_SETTINGS.uiVisibility },
    modelSettings: { ...DEFAULT_SETTINGS.modelSettings },
    vadSettings: { ...DEFAULT_SETTINGS.vadSettings },
    generationSettings: { ...DEFAULT_SETTINGS.generationSettings },
    avatarMappings: { ...DEFAULT_SETTINGS.avatarMappings },
    defaultAvatar: DEFAULT_SETTINGS.defaultAvatar,
    theme: DEFAULT_SETTINGS.theme,
  };
}

export class Store {
  static getSettings(): AppSettings {
    const data = localStorage.getItem('gemini_avatar_settings');
    if (data) {
      try {
        const parsed = JSON.parse(data);
        return {
          uiVisibility: {
            ...DEFAULT_SETTINGS.uiVisibility,
            ...parsed.uiVisibility,
          },
          modelSettings: {
            ...DEFAULT_SETTINGS.modelSettings,
            ...parsed.modelSettings,
          },
          vadSettings: {
            ...DEFAULT_SETTINGS.vadSettings,
            ...parsed.vadSettings,
          },
          generationSettings: {
            ...DEFAULT_SETTINGS.generationSettings,
            ...parsed.generationSettings,
          },
          avatarMappings: {
            ...DEFAULT_SETTINGS.avatarMappings,
            ...parsed.avatarMappings,
          },
          defaultAvatar: parsed.defaultAvatar || DEFAULT_SETTINGS.defaultAvatar,
          theme: isTheme(parsed.theme) ? parsed.theme : DEFAULT_SETTINGS.theme,
        };
      } catch (e) {
        console.error('Failed to parse settings', e);
      }
    }
    return cloneDefaultSettings();
  }

  static saveSettings(settings: AppSettings) {
    localStorage.setItem('gemini_avatar_settings', JSON.stringify(settings));
    window.dispatchEvent(
      new CustomEvent('settings-updated', { detail: settings }),
    );
  }
}
