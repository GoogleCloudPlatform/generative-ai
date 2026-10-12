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

import type { GaTheme } from './theme/tokens';
import type { GaRadioOption } from './components/ui/ga-radio-group';
import { LitElement, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  Store,
  type AppSettings,
  type GenerationSettings,
  type ModelSettings,
  type VadSettings,
} from './store';
import { renderPresetThumb } from './preset-image';
import {
  DEFAULT_GREETINGS,
  DEFAULT_SYSTEM_INSTRUCTIONS,
  PRESET_VOICES,
  PRESETS,
  VOICE_SELECT_OPTIONS,
} from './domain/presets';
import { SettingsController } from './controllers/settings-controller';
import { showToast, type GaChangeDetail } from './theme/events';
import type { GaSelectOption } from './components/ui/ga-select';
import './components/ui';

interface ServerConfig {
  liveModel: string;
  liveLocation: string;
  imageModel: string;
  availableLiveModels: string[];
  availableLocations: string[];
  availableImageModels: string[];
}

const PRESET_OPTIONS: readonly GaSelectOption[] = PRESETS.map((p) => ({
  value: p,
  label: p,
}));

const START_SENSITIVITY_OPTIONS: readonly GaSelectOption[] = [
  { value: '', label: 'Default (server)' },
  {
    value: 'START_SENSITIVITY_HIGH',
    label: 'High \u2014 interrupt more eagerly',
  },
  {
    value: 'START_SENSITIVITY_LOW',
    label: 'Low \u2014 ignore background noise',
  },
];

const END_SENSITIVITY_OPTIONS: readonly GaSelectOption[] = [
  { value: '', label: 'Default (server)' },
  { value: 'END_SENSITIVITY_HIGH', label: 'High \u2014 reply sooner' },
  { value: 'END_SENSITIVITY_LOW', label: 'Low \u2014 wait through pauses' },
];

const ACTIVITY_HANDLING_OPTIONS: readonly GaSelectOption[] = [
  { value: '', label: 'Default (Barge-in enabled)' },
  {
    value: 'START_OF_ACTIVITY_INTERRUPTS',
    label: 'Interrupts \u2014 user speech cuts off model turn',
  },
  {
    value: 'NO_INTERRUPTION',
    label: 'No Interruption \u2014 finish speaking before listening',
  },
];

const THEME_OPTIONS: readonly GaRadioOption[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'Match system' },
];

/**
 * View orchestrator (`<app-settings>`) built with standardized `<ga-select>`,
 * `<ga-field>`, `<ga-button>`, `SettingsController`, and `showToast()`.
 */
@customElement('app-settings')
export class AppSettingsEl extends LitElement {
  private readonly settingsCtrl = new SettingsController(this);

  @state() private settings: AppSettings = this.settingsCtrl.value;
  @state() private selectedPreset: string =
    this.settingsCtrl.value.defaultAvatar || 'Ben';

  @state() private draftVoice = '';
  @state() private draftWelcome = '';
  @state() private draftSystem = '';

  @state() private serverConfig: ServerConfig | null = null;

  protected override createRenderRoot() {
    return this;
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this.settings = this.settingsCtrl.value;
    this.loadDraft(this.selectedPreset);
    this.fetchServerConfig();
  }

  private async fetchServerConfig() {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      this.serverConfig = await res.json();
    } catch (e) {
      console.error('Failed to load server config', e);
      showToast(
        'Could not load server model configuration; using defaults.',
        'danger',
      );
    }
  }

  private loadDraft(preset: string) {
    const mapping = this.settings.avatarMappings[preset];
    if (mapping) {
      this.draftVoice = mapping.voiceName || '';
      this.draftWelcome = mapping.welcomeMessage || '';
      this.draftSystem = mapping.systemInstruction || '';
    } else {
      this.draftVoice = '';
      this.draftWelcome = '';
      this.draftSystem = '';
    }
  }

  private saveSection(
    patch: Partial<AppSettings>,
    toastMessage = 'Settings saved!',
  ) {
    const persisted = Store.getSettings();
    const merged: AppSettings = {
      ...persisted,
      ...patch,
    };
    this.settings = {
      ...this.settings,
      ...patch,
    };
    this.settingsCtrl.save(merged);
    showToast(toastMessage, 'success');
  }

  private updateModelSetting(key: keyof ModelSettings, value: string) {
    this.settings = {
      ...this.settings,
      modelSettings: {
        ...this.settings.modelSettings,
        [key]: value,
      },
    };
  }

  private resetModelSettings() {
    const resetMs: ModelSettings = {
      liveModel: '',
      liveLocation: '',
      imageModel: '',
    };
    const persisted = Store.getSettings();
    this.settings = {
      ...this.settings,
      modelSettings: resetMs,
    };
    this.settingsCtrl.save({ ...persisted, modelSettings: resetMs });
    showToast('Model settings reset to server defaults (.env)', 'primary');
  }

  /**
   * Updates one VAD field. An empty string or a non-finite number deletes the
   * key outright rather than storing a falsy value, because the backend treats
   * the presence of any VAD field as intent to override the server defaults.
   */
  private updateVadSetting(key: keyof VadSettings, value: string) {
    const next: VadSettings = { ...this.settings.vadSettings };
    const trimmed = value.trim();

    if (trimmed === '') {
      delete next[key];
    } else if (key === 'silenceDurationMs' || key === 'prefixPaddingMs') {
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        delete next[key];
      } else {
        next[key] = Math.round(parsed);
      }
    } else {
      next[key] = trimmed as never;
    }

    this.settings = { ...this.settings, vadSettings: next };
  }

  private resetVadSettings() {
    const persisted = Store.getSettings();
    this.settings = { ...this.settings, vadSettings: {} };
    this.settingsCtrl.save({ ...persisted, vadSettings: {} });
    showToast('Voice detection settings reset to server defaults', 'primary');
  }

  private updateNumericGenSetting(
    key:
      | 'temperature'
      | 'topP'
      | 'topK'
      | 'maxOutputTokens'
      | 'compressionTriggerTokens',
    rawValue: string,
  ) {
    const next: GenerationSettings = { ...this.settings.generationSettings };
    const trimmed = rawValue.trim();
    if (trimmed === '') {
      delete next[key];
    } else {
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed) || parsed < 0) {
        delete next[key];
      } else if (
        key === 'topK' ||
        key === 'maxOutputTokens' ||
        key === 'compressionTriggerTokens'
      ) {
        if (parsed <= 0) {
          delete next[key];
        } else {
          next[key] = Math.round(parsed);
        }
      } else {
        next[key] = parsed;
      }
    }
    this.settings = { ...this.settings, generationSettings: next };
  }

  private updateBooleanGenSetting(
    key: 'proactiveAudio' | 'contextWindowCompression',
    checked: boolean,
  ) {
    this.settings = {
      ...this.settings,
      generationSettings: {
        ...this.settings.generationSettings,
        [key]: checked,
      },
    };
  }

  private updateAdaptationPhrases(rawValue: string) {
    const next: GenerationSettings = { ...this.settings.generationSettings };
    const phrases = rawValue
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (phrases.length === 0) {
      delete next.adaptationPhrases;
    } else {
      next.adaptationPhrases = phrases;
    }
    this.settings = { ...this.settings, generationSettings: next };
  }

  private resetGenerationSettings() {
    const resetGen: GenerationSettings = {
      contextWindowCompression: true,
    };
    const persisted = Store.getSettings();
    this.settings = {
      ...this.settings,
      generationSettings: resetGen,
    };
    this.settingsCtrl.save({ ...persisted, generationSettings: resetGen });
    showToast(
      'Live capabilities & generation settings reset to defaults',
      'primary',
    );
  }

  private saveMapping() {
    const persisted = Store.getSettings();
    const nextMappings = {
      ...persisted.avatarMappings,
      [this.selectedPreset]: {
        voiceName: this.draftVoice,
        welcomeMessage: this.draftWelcome,
        systemInstruction: this.draftSystem,
      },
    };
    this.settings = { ...this.settings, avatarMappings: nextMappings };
    this.settingsCtrl.save({ ...persisted, avatarMappings: nextMappings });
    showToast(`Saved mapping for ${this.selectedPreset}`, 'success');
  }

  private resetDefaults() {
    const persisted = Store.getSettings();
    const nextMappings = { ...persisted.avatarMappings };
    delete nextMappings[this.selectedPreset];
    this.settings = { ...this.settings, avatarMappings: nextMappings };
    this.settingsCtrl.save({ ...persisted, avatarMappings: nextMappings });
    this.loadDraft(this.selectedPreset);
    showToast(`Reset to defaults for ${this.selectedPreset}`, 'primary');
  }

  private updateVisibility(
    key: keyof AppSettings['uiVisibility'],
    value: boolean,
  ) {
    this.settings = {
      ...this.settings,
      uiVisibility: { ...this.settings.uiVisibility, [key]: value },
    };
  }

  protected override render() {
    const ms = this.settings.modelSettings || {};
    const vad = this.settings.vadSettings || {};
    const gen = this.settings.generationSettings || {};
    const defaultLive = this.serverConfig?.liveModel || 'gemini-3.8-live';
    const defaultLoc = this.serverConfig?.liveLocation || 'us-central1';
    const defaultImg =
      this.serverConfig?.imageModel || 'gemini-nano-banana-2.1';

    const liveModels = this.serverConfig?.availableLiveModels || [
      'gemini-3.8-live',
    ];
    const locations = this.serverConfig?.availableLocations || [
      'us-central1',
      'global',
    ];
    const imageModels = this.serverConfig?.availableImageModels || [
      'gemini-nano-banana-2.1',
      'gemini-3.1-flash-image',
      'gemini-3-pro-image',
      'gemini-3.1-flash-lite-image',
    ];

    const liveModelOptions: GaSelectOption[] = [
      { value: '', label: `Default (.env: ${defaultLive})` },
      ...liveModels.map((m) => ({ value: m, label: m })),
    ];
    const locationOptions: GaSelectOption[] = [
      { value: '', label: `Default (.env: ${defaultLoc})` },
      ...locations.map((l) => ({ value: l, label: l })),
    ];
    const imageModelOptions: GaSelectOption[] = [
      { value: '', label: `Default (.env: ${defaultImg})` },
      ...imageModels.map((im) => ({ value: im, label: im })),
    ];

    const voiceOverrideOptions: GaSelectOption[] = [
      {
        value: '',
        label: `-- Default (${PRESET_VOICES[this.selectedPreset] || 'Puck'}) --`,
      },
      ...VOICE_SELECT_OPTIONS,
    ];

    return html`
      <div
        class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/20 p-8 flex flex-col gap-8 max-w-4xl w-full"
      >
        <ga-section-header
          size="page"
          heading="Settings"
          subheading="Configure AI models, Google Cloud regions, UI visibility, and custom avatar personas."
        ></ga-section-header>

        <!-- AI Models & Regions Configuration -->
        <section class="border-t border-outline-variant/20 pt-6">
          <ga-section-header
            class="block mb-4"
            heading="AI Models &amp; Regions"
            subheading="Configure models and endpoints. Leave as &quot;Default&quot; to honor values provided by the backend .env."
            action-label="Reset to .env Defaults"
            @ga-action="${this.resetModelSettings}"
          ></ga-section-header>

          <div
            class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-surface-container-low/50 p-6 rounded-2xl border border-outline-variant/20"
          >
            <ga-select
              label="Gemini Live Model"
              surface="container"
              .options="${liveModelOptions}"
              .value="${
                liveModels.includes(ms.liveModel || '')
                  ? ms.liveModel || ''
                  : ''
              }"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateModelSetting('liveModel', e.detail.value)}"
            ></ga-select>

            <ga-select
              label="Live Region / Location"
              surface="container"
              .options="${locationOptions}"
              .value="${
                locations.includes(ms.liveLocation || '')
                  ? ms.liveLocation || ''
                  : ''
              }"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateModelSetting('liveLocation', e.detail.value)}"
            ></ga-select>

            <div class="md:col-span-2">
              <ga-select
                label="Image Generation Model (Avatar Synthesis)"
                surface="container"
                .options="${imageModelOptions}"
                .value="${
                  imageModels.includes(ms.imageModel || '')
                    ? ms.imageModel || ''
                    : ''
                }"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateModelSetting('imageModel', e.detail.value)}"
              ></ga-select>
            </div>
          </div>

          <div class="mt-4 flex justify-end">
            <ga-button
              variant="primary"
              label="Save Model Settings"
              @click="${() =>
                this.saveSection(
                  { modelSettings: this.settings.modelSettings },
                  'Model settings saved!',
                )}"
            ></ga-button>
          </div>
        </section>

        <!-- Voice Detection (VAD) -->
        <section class="border-t border-outline-variant/20 pt-6">
          <ga-section-header
            class="block mb-4"
            heading="Voice Detection (VAD)"
            subheading="Controls how the model decides when you have started and stopped speaking. Leave everything blank to use the server defaults — any field you set is sent as an explicit override."
            action-label="Reset to defaults"
            @ga-action="${this.resetVadSettings}"
          ></ga-section-header>

          <div
            class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-surface-container-low/50 p-6 rounded-2xl border border-outline-variant/20"
          >
            <ga-select
              label="Start of Speech Sensitivity"
              surface="container"
              supporting-text="Raise if barge-in feels sluggish; lower it in a noisy room."
              .options="${START_SENSITIVITY_OPTIONS}"
              .value="${vad.startOfSpeechSensitivity || ''}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVadSetting(
                  'startOfSpeechSensitivity',
                  e.detail.value,
                )}"
            ></ga-select>

            <ga-select
              label="End of Speech Sensitivity"
              surface="container"
              supporting-text="Lower it if you get cut off mid-thought."
              .options="${END_SENSITIVITY_OPTIONS}"
              .value="${vad.endOfSpeechSensitivity || ''}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVadSetting(
                  'endOfSpeechSensitivity',
                  e.detail.value,
                )}"
            ></ga-select>

            <ga-field
              label="Silence Duration (ms)"
              type="number"
              surface="container"
              .min="${0}"
              .step="${50}"
              placeholder="Default (server)"
              supporting-text="How long you must pause before your turn ends. Higher = more thinking room."
              .value="${vad.silenceDurationMs?.toString() ?? ''}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVadSetting('silenceDurationMs', e.detail.value)}"
            ></ga-field>

            <ga-field
              label="Prefix Padding (ms)"
              type="number"
              surface="container"
              .min="${0}"
              .step="${50}"
              placeholder="Default (server)"
              supporting-text="Audio kept from just before you start talking, so leading words aren't clipped."
              .value="${vad.prefixPaddingMs?.toString() ?? ''}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVadSetting('prefixPaddingMs', e.detail.value)}"
            ></ga-field>

            <div class="md:col-span-2">
              <ga-select
                label="Barge-In / Activity Handling"
                surface="container"
                supporting-text="Choose whether user speech interrupts an active response or waits until the model finishes speaking."
                .options="${ACTIVITY_HANDLING_OPTIONS}"
                .value="${vad.activityHandling || ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateVadSetting('activityHandling', e.detail.value)}"
              ></ga-select>
            </div>
          </div>

          <div class="mt-4 flex justify-end">
            <ga-button
              variant="primary"
              label="Save Voice Detection Settings"
              @click="${() =>
                this.saveSection(
                  { vadSettings: this.settings.vadSettings },
                  'Voice detection settings saved!',
                )}"
            ></ga-button>
          </div>
        </section>

        <!-- Gemini 3.8 Live Capabilities & Generation -->
        <section class="border-t border-outline-variant/20 pt-6">
          <ga-section-header
            class="block mb-4"
            heading="Live Capabilities &amp; Generation"
            subheading="Fine-tune Gemini 3.8 Live session behavior across both Avatar Studio and Live Audio modes, including sliding-window context compression, proactive audio, speech adaptation vocabulary, and sampling parameters."
            action-label="Reset to defaults"
            @ga-action="${this.resetGenerationSettings}"
          ></ga-section-header>

          <div
            class="flex flex-col gap-6 bg-surface-container-low/50 p-6 rounded-2xl border border-outline-variant/20"
          >
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ga-checkbox
                label="Context Window Compression (SlidingWindow)"
                description="Automatically truncates older turns so long 1 FPS vision + voice sessions never exceed context limits."
                .checked="${gen.contextWindowCompression ?? true}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateBooleanGenSetting(
                    'contextWindowCompression',
                    e.detail.checked ?? false,
                  )}"
              ></ga-checkbox>

              <ga-checkbox
                label="Proactive Audio (Gemini 3.8 &amp; Lite)"
                description="Allows the model to ignore background chatter or stay silent when speech is not directed at it."
                .checked="${Boolean(gen.proactiveAudio)}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateBooleanGenSetting(
                    'proactiveAudio',
                    e.detail.checked ?? false,
                  )}"
              ></ga-checkbox>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ga-field
                label="Speech Adaptation Phrases (comma-separated)"
                surface="container"
                placeholder="e.g. Kubernetes, gRPC, Gemini Live, BigQuery"
                supporting-text="Biases input ASR transcription toward domain-specific jargon and product names."
                .value="${(gen.adaptationPhrases ?? []).join(', ')}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateAdaptationPhrases(e.detail.value)}"
              ></ga-field>

              <ga-field
                label="Compression Trigger Tokens"
                type="number"
                surface="container"
                .min="${0}"
                .step="${1000}"
                placeholder="Default (server)"
                supporting-text="Optional token threshold that triggers sliding-window truncation."
                .value="${gen.compressionTriggerTokens?.toString() ?? ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateNumericGenSetting(
                    'compressionTriggerTokens',
                    e.detail.value,
                  )}"
              ></ga-field>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <ga-field
                label="Temperature"
                type="number"
                surface="container"
                .min="${0}"
                .max="${2}"
                .step="${0.1}"
                placeholder="Default"
                supporting-text="0.0 – 2.0"
                .value="${gen.temperature?.toString() ?? ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateNumericGenSetting('temperature', e.detail.value)}"
              ></ga-field>

              <ga-field
                label="Top P"
                type="number"
                surface="container"
                .min="${0}"
                .max="${1}"
                .step="${0.05}"
                placeholder="Default"
                supporting-text="0.0 – 1.0"
                .value="${gen.topP?.toString() ?? ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateNumericGenSetting('topP', e.detail.value)}"
              ></ga-field>

              <ga-field
                label="Top K"
                type="number"
                surface="container"
                .min="${1}"
                .max="${100}"
                .step="${1}"
                placeholder="Default"
                supporting-text="Token pool size"
                .value="${gen.topK?.toString() ?? ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateNumericGenSetting('topK', e.detail.value)}"
              ></ga-field>

              <ga-field
                label="Max Output Tokens"
                type="number"
                surface="container"
                .min="${1}"
                .step="${128}"
                placeholder="Default"
                supporting-text="Per-turn cap"
                .value="${gen.maxOutputTokens?.toString() ?? ''}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  this.updateNumericGenSetting(
                    'maxOutputTokens',
                    e.detail.value,
                  )}"
              ></ga-field>
            </div>
          </div>

          <div class="mt-4 flex justify-end">
            <ga-button
              variant="primary"
              label="Save Live Capabilities"
              @click="${() =>
                this.saveSection(
                  { generationSettings: this.settings.generationSettings },
                  'Live capabilities & generation settings saved!',
                )}"
            ></ga-button>
          </div>
        </section>

        <!-- Global Preferences -->
        <section class="border-t border-outline-variant/20 pt-6">
          <ga-section-header class="block mb-4" heading="Global Preferences"></ga-section-header>
          <div class="flex flex-col gap-4">
            <ga-radio-group
              label="Theme"
              appearance="chip"
              .options="${THEME_OPTIONS}"
              .value="${this.settings.theme}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.saveSection(
                  { theme: e.detail.value as GaTheme },
                  'Theme updated',
                )}"
            ></ga-radio-group>

            <ga-checkbox
              appearance="inline"
              label="Show &quot;Presets&quot; Tab"
              .checked="${this.settings.uiVisibility.showPresets}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVisibility(
                  'showPresets',
                  e.detail.checked ?? false,
                )}"
            ></ga-checkbox>
            <ga-checkbox
              appearance="inline"
              label="Show &quot;Upload / Camera&quot; Tab"
              .checked="${this.settings.uiVisibility.showUpload}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVisibility('showUpload', e.detail.checked ?? false)}"
            ></ga-checkbox>
            <ga-checkbox
              appearance="inline"
              label="Show &quot;Generate&quot; Tab"
              .checked="${this.settings.uiVisibility.showGenerate}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                this.updateVisibility(
                  'showGenerate',
                  e.detail.checked ?? false,
                )}"
            ></ga-checkbox>

            <div class="mt-6 pt-6 border-t border-outline-variant/20 max-w-xs">
              <ga-select
                label="Global Default Avatar"
                .options="${PRESET_OPTIONS}"
                .value="${this.settings.defaultAvatar || 'Ben'}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  (this.settings = {
                    ...this.settings,
                    defaultAvatar: e.detail.value,
                  })}"
              ></ga-select>
            </div>
            <div class="mt-4">
              <ga-button
                variant="tonal"
                label="Save Global Settings"
                @click="${() =>
                  this.saveSection(
                    {
                      uiVisibility: this.settings.uiVisibility,
                      defaultAvatar: this.settings.defaultAvatar,
                    },
                    'Global settings saved!',
                  )}"
              ></ga-button>
            </div>
          </div>
        </section>

        <!-- Avatar Mappings -->
        <section class="border-t border-outline-variant/20 pt-6">
          <ga-section-header class="block mb-4" heading="Avatar Mappings"></ga-section-header>

          <div class="flex flex-col md:flex-row gap-6">
            <!-- Preset Selector -->
            <div class="w-full md:w-1/3">
              <ga-select
                label="Select Avatar"
                .options="${PRESET_OPTIONS}"
                .value="${this.selectedPreset}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) => {
                  this.selectedPreset = e.detail.value;
                  this.loadDraft(this.selectedPreset);
                }}"
              ></ga-select>

              <div class="mt-6 flex justify-center">
                ${
                  this.selectedPreset
                    ? renderPresetThumb(
                        this.selectedPreset,
                        this,
                        'w-32 h-32 rounded-full object-cover object-top border-4 border-surface-container-highest',
                        'w-32 h-32 rounded-full text-5xl border-4 border-surface-container-highest',
                      )
                    : nothing
                }
              </div>
            </div>

            <!-- Mapping Editor -->
            <div class="w-full md:w-2/3 flex flex-col gap-4">
              <ga-select
                label="Voice Override"
                .options="${voiceOverrideOptions}"
                .value="${this.draftVoice}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  (this.draftVoice = e.detail.value)}"
              ></ga-select>

              <ga-field
                label="Custom Welcome Message"
                multiline
                .rows="${3}"
                placeholder="${
                  DEFAULT_GREETINGS[this.selectedPreset] ||
                  'Hello! I am ready to assist you.'
                }"
                .value="${this.draftWelcome}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  (this.draftWelcome = e.detail.value)}"
              ></ga-field>

              <ga-field
                label="System Instruction / Persona"
                multiline
                .rows="${4}"
                placeholder="${
                  DEFAULT_SYSTEM_INSTRUCTIONS[this.selectedPreset] ||
                  'You are a helpful AI assistant.'
                }"
                .value="${this.draftSystem}"
                @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                  (this.draftSystem = e.detail.value)}"
              ></ga-field>

              <div class="mt-4 flex flex-col md:flex-row gap-3">
                <ga-button
                  class="flex-1"
                  full-width
                  variant="primary"
                  label="Save Avatar Mapping"
                  @click="${this.saveMapping}"
                ></ga-button>
                <ga-button
                  variant="danger"
                  label="Reset to Defaults"
                  @click="${this.resetDefaults}"
                ></ga-button>
              </div>
            </div>
          </div>
        </section>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-settings': AppSettingsEl;
  }
}
