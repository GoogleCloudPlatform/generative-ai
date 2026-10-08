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

import { LitElement, html } from 'lit';
import { customElement, query, state } from 'lit/decorators.js';
import { AVATAR_PORTRAIT, resizeAndCropImage } from './image-utils';
import {
  buildSessionTuningPayload,
  PRESET_VOICES,
  VOICE_SELECT_OPTIONS,
  type AvatarConfigEvent,
  type UploadTransformMode,
} from './domain/presets';
import { SettingsController } from './controllers/settings-controller';
import { showToast, type GaChangeDetail } from './theme/events';
import type { GaSegmentOption } from './components/ui/ga-segmented-control';
import type {
  AvatarTransformModeChangeDetail,
  AvatarUploadCaptureDetail,
  AvatarUploadStudio,
} from './components/avatar/avatar-upload-studio';
import type { AvatarPromptDetail } from './components/avatar/avatar-prompt-generator';
import type { AvatarContextChangeDetail } from './components/avatar/avatar-context-drawer';
import './components/ui';
import './components/avatar';

export type { AvatarConfigEvent, UploadTransformMode };

/**
 * View orchestrator (`<avatar-setup>`) composing the Tier 1 UI primitives and
 * Tier 2 Avatar domain components (`<avatar-preset-picker>`,
 * `<avatar-upload-studio>`, `<avatar-prompt-generator>`, `<avatar-context-drawer>`,
 * and `<avatar-preview-card>`).
 *
 * @fires connect - When the user starts a session. Detail: `AvatarConfigEvent`.
 */
@customElement('avatar-setup')
export class AvatarSetup extends LitElement {
  private readonly settingsCtrl = new SettingsController(this, () => {
    this.syncPresetDefaults(this.selectedPreset);
    this.updateModeIfNeeded();
  });

  @state() private mode: 'preset' | 'upload' | 'generate' = 'preset';
  @state() private selectedPreset: string =
    this.settingsCtrl.value.defaultAvatar || 'Ben';
  @state() private customImageBase64 = '';
  @state() private rawUploadBase64 = '';
  @state() private uploadTransformMode: UploadTransformMode = 'avatar';
  private transformedCache: Partial<Record<UploadTransformMode, string>> = {};

  @state() private prompt = '';
  @state() private isProcessing = false;
  @state() private voiceName: string =
    PRESET_VOICES[this.settingsCtrl.value.defaultAvatar || 'Ben'] || 'Puck';

  @state() private systemInstruction = '';
  @state() private welcomeMessage = '';
  @state() private groundingContext = '';
  @state() private enableGoogleSearch = true;
  @state() private enableToolCalling = true;

  @query('avatar-upload-studio') private uploadStudioEl?: AvatarUploadStudio;

  override connectedCallback(): void {
    super.connectedCallback();
    this.syncPresetDefaults(this.selectedPreset);
    this.updateModeIfNeeded();
  }

  protected override createRenderRoot() {
    return this;
  }

  private get appSettings() {
    return this.settingsCtrl.value;
  }

  private syncPresetDefaults(preset: string) {
    const mapping = this.appSettings.avatarMappings[preset];
    this.voiceName = mapping?.voiceName || PRESET_VOICES[preset] || 'Puck';
    this.systemInstruction = mapping?.systemInstruction || '';
    this.welcomeMessage = mapping?.welcomeMessage || '';
  }

  private updateModeIfNeeded() {
    const vis = this.appSettings.uiVisibility;
    if (this.mode === 'preset' && !vis.showPresets) {
      this.mode = vis.showUpload
        ? 'upload'
        : vis.showGenerate
          ? 'generate'
          : 'preset';
    } else if (this.mode === 'upload' && !vis.showUpload) {
      this.mode = vis.showPresets
        ? 'preset'
        : vis.showGenerate
          ? 'generate'
          : 'preset';
    } else if (this.mode === 'generate' && !vis.showGenerate) {
      this.mode = vis.showPresets
        ? 'preset'
        : vis.showUpload
          ? 'upload'
          : 'preset';
    }
  }

  private modeSegments(): readonly GaSegmentOption<
    'preset' | 'upload' | 'generate'
  >[] {
    const vis = this.appSettings.uiVisibility;
    return [
      { value: 'preset', label: 'Presets', hidden: !vis.showPresets },
      { value: 'upload', label: 'Upload / Camera', hidden: !vis.showUpload },
      { value: 'generate', label: 'Generate', hidden: !vis.showGenerate },
    ];
  }

  private handleModeChange(e: CustomEvent<GaChangeDetail>) {
    const next = e.detail.value as 'preset' | 'upload' | 'generate';
    if (next !== 'upload') {
      this.uploadStudioEl?.stopCamera();
    }
    this.mode = next;
  }

  private async handleUploadCapture(e: CustomEvent<AvatarUploadCaptureDetail>) {
    const { dataUrl, source } = e.detail;
    this.isProcessing = true;
    try {
      const portraitCropped = await resizeAndCropImage(
        dataUrl,
        AVATAR_PORTRAIT.width,
        AVATAR_PORTRAIT.height,
      );
      const autoCropped =
        source === 'file' ? await resizeAndCropImage(dataUrl) : portraitCropped;
      this.rawUploadBase64 = portraitCropped;
      this.transformedCache = { none: autoCropped };
      await this.applyUploadTransformMode(this.uploadTransformMode);
    } catch (err) {
      console.error('Failed to process image:', err);
      showToast('Failed to process image. Please try again.', 'danger');
    } finally {
      this.isProcessing = false;
    }
  }

  private async selectUploadTransformMode(mode: UploadTransformMode) {
    if (this.uploadTransformMode === mode && this.customImageBase64) return;
    this.uploadTransformMode = mode;
    if (this.rawUploadBase64) {
      this.isProcessing = true;
      try {
        await this.applyUploadTransformMode(mode);
      } finally {
        this.isProcessing = false;
      }
    }
  }

  private async applyUploadTransformMode(mode: UploadTransformMode) {
    if (!this.rawUploadBase64) return;

    const cached = this.transformedCache[mode];
    if (cached) {
      this.customImageBase64 = cached;
      return;
    }

    const prompt =
      mode === 'remove-bg'
        ? 'Keep this exact person with 100% photographic fidelity, preserving their exact face, skin texture, hair, expression, lighting, and clothing unchanged. Remove the background and replace it with a clean, soft neutral dark-gray studio portrait backdrop with subtle rim lighting.'
        : 'Transform this portrait into a highly detailed, 2K resolution, Pixar-style 3D animated character portrait, maintaining the original expression and core features but with stylized, smooth cinematic lighting and proportions.';

    try {
      const response = await fetch('/api/generate-avatar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          image: this.rawUploadBase64,
          model: this.appSettings.modelSettings?.imageModel || undefined,
        }),
      });
      if (!response.ok) {
        const errText = (await response.text()).trim();
        throw new Error(errText || 'Failed to transform image');
      }
      const data = await response.json();
      if (data.image) {
        const processed = await resizeAndCropImage(
          data.image,
          AVATAR_PORTRAIT.width,
          AVATAR_PORTRAIT.height,
        );
        this.transformedCache[mode] = processed;
        this.customImageBase64 = processed;
      }
    } catch (err) {
      console.error(err);
      const reason =
        err instanceof Error && err.message ? ` (${err.message})` : '';
      showToast(
        mode === 'remove-bg'
          ? `Failed to remove background${reason}; falling back to cropped original.`
          : `Failed to transform avatar${reason}; falling back to cropped original.`,
        'danger',
      );
      this.customImageBase64 = this.rawUploadBase64;
    }
  }

  private async handleGenerate() {
    this.isProcessing = true;
    try {
      const response = await fetch('/api/generate-avatar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: this.prompt,
          model: this.appSettings.modelSettings?.imageModel || undefined,
        }),
      });
      if (!response.ok) {
        const errText = (await response.text()).trim();
        throw new Error(errText || 'Failed to generate image');
      }
      const data = await response.json();
      if (data.image) {
        this.customImageBase64 = await resizeAndCropImage(
          data.image,
          AVATAR_PORTRAIT.width,
          AVATAR_PORTRAIT.height,
        );
      }
    } catch (err) {
      console.error(err);
      const msg =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to generate avatar';
      showToast(msg, 'danger');
    } finally {
      this.isProcessing = false;
    }
  }

  private handleContextChange(e: CustomEvent<AvatarContextChangeDetail>) {
    this.systemInstruction = e.detail.systemInstruction;
    this.welcomeMessage = e.detail.welcomeMessage;
    this.groundingContext = e.detail.groundingContext;
  }

  private handleConnect() {
    const presetMapping =
      this.mode === 'preset'
        ? this.appSettings.avatarMappings[this.selectedPreset]
        : undefined;
    const evt = new CustomEvent<AvatarConfigEvent>('connect', {
      detail: {
        ...buildSessionTuningPayload(this.appSettings),
        avatarType: this.mode === 'preset' ? 'preset' : 'custom',
        avatarData:
          this.mode === 'preset' ? this.selectedPreset : this.customImageBase64,
        voiceName: this.voiceName,
        welcomeMessage:
          this.welcomeMessage.trim() || presetMapping?.welcomeMessage || '',
        systemInstruction:
          this.systemInstruction.trim() ||
          presetMapping?.systemInstruction ||
          '',
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
            heading="Avatar Anchor"
            subheading="Select a visual base for your Gemini Live session."
          ></ga-section-header>

          <!-- Segmented Mode Tabs -->
          <ga-segmented-control
            aria-label="Avatar source mode"
            .options="${this.modeSegments()}"
            .value="${this.mode}"
            @ga-change="${this.handleModeChange}"
          ></ga-segmented-control>

          <!-- Dynamic Mode Panel -->
          <div class="flex-1">
            ${
              this.mode === 'preset'
                ? html`
                  <avatar-preset-picker
                    .value="${this.selectedPreset}"
                    @ga-change="${(e: CustomEvent<GaChangeDetail>) => {
                      this.selectedPreset = e.detail.value;
                      this.syncPresetDefaults(this.selectedPreset);
                    }}"
                  ></avatar-preset-picker>
                `
                : ''
            }
            ${
              this.mode === 'upload'
                ? html`
                  <avatar-upload-studio
                    .transformMode="${this.uploadTransformMode}"
                    ?processing="${this.isProcessing}"
                    ?has-raw-upload="${Boolean(this.rawUploadBase64)}"
                    @avatar-upload-capture="${this.handleUploadCapture}"
                    @avatar-transform-mode-change="${(
                      e: CustomEvent<AvatarTransformModeChangeDetail>,
                    ) => this.selectUploadTransformMode(e.detail.mode)}"
                  ></avatar-upload-studio>
                `
                : ''
            }
            ${
              this.mode === 'generate'
                ? html`
                  <avatar-prompt-generator
                    .prompt="${this.prompt}"
                    ?processing="${this.isProcessing}"
                    @avatar-prompt-change="${(
                      e: CustomEvent<AvatarPromptDetail>,
                    ) => (this.prompt = e.detail.prompt)}"
                    @avatar-generate="${this.handleGenerate}"
                  ></avatar-prompt-generator>
                `
                : ''
            }
          </div>

          <!-- Voice Selection, Agent Tools & Advanced Context -->
          <div
            class="mt-auto pt-6 border-t border-outline-variant/20 flex flex-col gap-4"
          >
            <ga-select
              label="Voice Persona"
              .options="${VOICE_SELECT_OPTIONS}"
              .value="${this.voiceName}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
                (this.voiceName = e.detail.value)}"
            ></ga-select>

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

            <avatar-context-drawer
              .systemInstruction="${this.systemInstruction}"
              .welcomeMessage="${this.welcomeMessage}"
              .groundingContext="${this.groundingContext}"
              @avatar-context-change="${this.handleContextChange}"
            ></avatar-context-drawer>
          </div>
        </div>

        <!-- Right Side: Preview & Action -->
        <div
          class="w-full md:w-1/2 p-8 bg-surface-container-low flex flex-col items-center justify-center relative min-h-[400px]"
        >
          <avatar-preview-card
            .mode="${this.mode}"
            .selectedPreset="${this.selectedPreset}"
            .customImageBase64="${this.customImageBase64}"
            ?processing="${this.isProcessing}"
          ></avatar-preview-card>

          <div class="absolute bottom-8 left-0 right-0 flex justify-center">
            <ga-button
              variant="primary"
              size="lg"
              label="Connect to Avatar"
              trailing-icon="bolt"
              ?disabled="${
                (this.mode !== 'preset' && !this.customImageBase64) ||
                this.isProcessing
              }"
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
    'avatar-setup': AvatarSetup;
  }
}
