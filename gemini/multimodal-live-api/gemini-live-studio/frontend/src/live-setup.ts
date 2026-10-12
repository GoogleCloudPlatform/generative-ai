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

import { LitElement, html, nothing } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  buildSessionTuningPayload,
  DEFAULT_GREETINGS,
  DEFAULT_SYSTEM_INSTRUCTIONS,
  PRESET_VOICES,
  PRESETS,
  VOICE_SELECT_OPTIONS,
  VOICES,
  type LiveConfigEvent,
} from './domain/presets';
import { SettingsController } from './controllers/settings-controller';
import type { GaChangeDetail } from './theme/events';
import type { AvatarContextChangeDetail } from './components/avatar/avatar-context-drawer';
import { renderIcon } from './components/ui/icons';
import type { GaRadioOption } from './components/ui/ga-radio-group';
import './components/ui';
import './components/avatar/avatar-context-drawer';

export type { LiveConfigEvent };

const PERSONA_OPTIONS: readonly GaRadioOption[] = [
  { value: '', label: 'Default Assistant' },
  ...PRESETS.map((name) => ({ value: name, label: name })),
];

/**
 * View orchestrator (`<live-setup>`) for the audio-first Gemini 3.8 Live mode
 * (`/ws/live` — Voice + Vision, no video avatar anchor).
 *
 * @fires connect - When the user starts a session. Detail: `LiveConfigEvent`.
 */
@customElement('live-setup')
export class LiveSetup extends LitElement {
  private readonly settingsCtrl = new SettingsController(this);

  @state() private selectedPersona = '';
  @state() private voiceName = 'Puck';
  @state() private systemInstruction = '';
  @state() private welcomeMessage = '';
  @state() private groundingContext = '';
  @state() private enableGoogleSearch = true;
  @state() private enableToolCalling = true;

  protected override createRenderRoot() {
    return this;
  }

  private get appSettings() {
    return this.settingsCtrl.value;
  }

  private selectPersonaTemplate(persona: string) {
    this.selectedPersona = persona;
    if (!persona) {
      this.voiceName = 'Puck';
      this.systemInstruction = '';
      this.welcomeMessage = '';
      return;
    }
    const mapping = this.appSettings.avatarMappings[persona];
    this.voiceName = mapping?.voiceName || PRESET_VOICES[persona] || 'Puck';
    this.systemInstruction =
      mapping?.systemInstruction || DEFAULT_SYSTEM_INSTRUCTIONS[persona] || '';
    this.welcomeMessage =
      mapping?.welcomeMessage || DEFAULT_GREETINGS[persona] || '';
  }

  private handleContextChange(e: CustomEvent<AvatarContextChangeDetail>) {
    this.systemInstruction = e.detail.systemInstruction;
    this.welcomeMessage = e.detail.welcomeMessage;
    this.groundingContext = e.detail.groundingContext;
  }

  private handleConnect() {
    const evt = new CustomEvent<LiveConfigEvent>('connect', {
      detail: {
        ...buildSessionTuningPayload(this.appSettings),
        voiceName: this.voiceName,
        welcomeMessage: this.welcomeMessage.trim() || undefined,
        systemInstruction: this.systemInstruction.trim() || undefined,
        groundingContext: this.groundingContext.trim() || undefined,
        enableGoogleSearch: this.enableGoogleSearch,
        enableToolCalling: this.enableToolCalling,
      },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(evt);
  }

  protected override render() {
    const selectedVoiceObj = VOICES.find((v) => v.name === this.voiceName);
    const voiceTone = selectedVoiceObj?.tone || 'Natural';

    return html`
      <div
        class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/20 overflow-hidden flex flex-col md:flex-row"
      >
        <!-- Left Side: Configuration Controls -->
        <div
          class="w-full md:w-1/2 p-8 border-b md:border-b-0 md:border-r border-outline-variant/20 flex flex-col gap-6"
        >
          <ga-section-header
            size="page"
            heading="Live Audio &amp; Vision"
            subheading="Low-latency voice, webcam, and screen-share conversation with Gemini 3.8 Live — no video avatar required."
          ></ga-section-header>

          <!-- Optional Quick Persona Templates -->
          <ga-radio-group
            label="Persona Preset (Optional)"
            label-style="eyebrow"
            appearance="chip"
            .options="${PERSONA_OPTIONS}"
            .value="${this.selectedPersona}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
              this.selectPersonaTemplate(e.detail.value)}"
          ></ga-radio-group>

          <!-- Voice Selection -->
          <ga-select
            label="Voice Persona"
            .options="${VOICE_SELECT_OPTIONS}"
            .value="${this.voiceName}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
              (this.voiceName = e.detail.value)}"
          ></ga-select>

          <!-- Agent Tools: Google Search Grounding & Interactive Info Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ga-checkbox
              label="Google Search"
              description="Live web grounding"
              icon="globe"
              .checked="${this.enableGoogleSearch}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                (this.enableGoogleSearch = e.detail.checked ?? false)}"
            ></ga-checkbox>
            <ga-checkbox
              label="Info Cards"
              description="Function calling UI"
              icon="bolt"
              .checked="${this.enableToolCalling}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                (this.enableToolCalling = e.detail.checked ?? false)}"
            ></ga-checkbox>
          </div>

          <!-- Shared Persona, Greeting & Reference Material Drawer -->
          <div class="mt-auto pt-4 border-t border-outline-variant/20">
            <avatar-context-drawer
              .systemInstruction="${this.systemInstruction}"
              .welcomeMessage="${this.welcomeMessage}"
              .groundingContext="${this.groundingContext}"
              @avatar-context-change="${this.handleContextChange}"
            ></avatar-context-drawer>
          </div>
        </div>

        <!-- Right Side: Audio Orb Preview & Action -->
        <div
          class="w-full md:w-1/2 p-8 bg-surface-container-low flex flex-col items-center justify-center relative min-h-[420px]"
        >
          <div
            class="w-64 h-80 bg-surface-container-highest rounded-2xl shadow-lg border border-outline-variant/20 flex flex-col items-center justify-center p-6 relative overflow-hidden gap-5"
          >
            <!-- Ambient Radial Orb Preview -->
            <div class="relative flex items-center justify-center w-36 h-36">
              <div
                class="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse"
              ></div>
              <div
                class="w-28 h-28 rounded-full bg-gradient-to-br from-viz-speaking-highlight via-primary to-viz-night shadow-xl flex items-center justify-center text-on-primary"
              >
                ${renderIcon('mic', 'w-10 h-10')}
              </div>
            </div>

            <div class="flex flex-col items-center gap-1.5 text-center z-10">
              <span class="text-base font-bold text-on-surface">
                ${this.voiceName} (${voiceTone})
              </span>
              <span class="text-xs text-on-surface-variant">
                ${
                  this.selectedPersona
                    ? `${this.selectedPersona} Persona`
                    : '24kHz Native Audio + 1 FPS Vision'
                }
              </span>
            </div>

            <div class="flex flex-wrap items-center justify-center gap-1.5">
              ${
                this.enableGoogleSearch
                  ? html`<ga-badge
                    label="Google Search"
                    tone="primary"
                    pill
                  ></ga-badge>`
                  : nothing
              }
              ${
                this.enableToolCalling
                  ? html`<ga-badge
                    label="Info Cards"
                    tone="primary"
                    pill
                  ></ga-badge>`
                  : nothing
              }
              ${
                this.groundingContext.trim()
                  ? html`<ga-badge
                    label="Grounded Context"
                    tone="primary"
                    pill
                  ></ga-badge>`
                  : nothing
              }
            </div>
          </div>

          <div class="mt-8 flex justify-center">
            <ga-button
              variant="primary"
              size="lg"
              label="Start Live Session"
              trailing-icon="bolt"
              @click="${this.handleConnect}"
            ></ga-button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'live-setup': LiveSetup;
  }
}
