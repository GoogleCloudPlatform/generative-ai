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
import { customElement, property } from 'lit/decorators.js';
import { renderPresetThumb } from '../../preset-image';
import { renderIcon } from '../ui/icons';

/**
 * Domain component (`<avatar-preview-card>`) rendering the 9:16 portrait
 * preview card, loading pulse, hover caption, or empty placeholder state.
 */
@customElement('avatar-preview-card')
export class AvatarPreviewCard extends LitElement {
  @property({ type: String }) mode: 'preset' | 'upload' | 'generate' = 'preset';
  @property({ type: String, attribute: 'selected-preset' }) selectedPreset =
    'Ben';
  @property({ attribute: false }) customImageBase64 = '';
  @property({ type: Boolean, attribute: 'processing' }) isProcessing = false;

  protected override createRenderRoot() {
    return this;
  }

  protected override render() {
    if (this.isProcessing) {
      return html`
        <div
          aria-busy="true"
          class="w-48 h-80 bg-surface-container rounded-2xl animate-pulse flex items-center justify-center shadow-inner"
        >
          ${renderIcon('spinner', 'h-8 w-8 text-primary')}
        </div>
      `;
    }

    if (this.mode === 'preset') {
      return html`
        <div
          class="w-48 h-80 rounded-2xl overflow-hidden shadow-2xl ring-4 ring-surface-container-lowest relative group bg-surface-container"
        >
          ${renderPresetThumb(
            this.selectedPreset,
            this,
            'w-full h-full object-cover object-top transition-transform duration-700 group-hover:scale-105',
            'w-full h-full text-8xl',
          )}
          <div
            class="absolute inset-0 bg-gradient-to-t from-scrim/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-6"
          >
            <span class="text-on-primary text-sm font-medium tracking-wide">
              ${this.selectedPreset}
            </span>
          </div>
        </div>
      `;
    }

    if (this.customImageBase64) {
      return html`
        <div
          class="w-48 h-80 rounded-2xl overflow-hidden shadow-2xl ring-4 ring-surface-container-lowest relative group"
        >
          <img
            src="${this.customImageBase64}"
            class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            alt="Custom Avatar"
          />
          <div
            class="absolute inset-0 bg-gradient-to-t from-scrim/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-6"
          >
            <span class="text-on-primary text-sm font-medium tracking-wide">
              Custom Avatar
            </span>
          </div>
        </div>
      `;
    }

    return html`
      <div
        class="w-48 h-80 border-2 border-dashed border-outline-variant/30 rounded-2xl flex flex-col items-center justify-center text-on-surface-variant text-center p-6"
      >
        ${renderIcon('image', 'w-8 h-8 mb-3 opacity-50')}
        <span class="text-sm">No image selected</span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-preview-card': AvatarPreviewCard;
  }
}
