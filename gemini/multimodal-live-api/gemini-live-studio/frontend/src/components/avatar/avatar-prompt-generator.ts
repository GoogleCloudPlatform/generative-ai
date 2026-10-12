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
import type { GaChangeDetail } from '../../theme/events';
import '../ui/ga-button';
import '../ui/ga-field';

export interface AvatarPromptDetail {
  prompt: string;
}

/**
 * Prompt-to-avatar generator (`<avatar-prompt-generator>`): a prompt field and
 * a Generate button (Gemini Image).
 *
 * @fires avatar-prompt-change - On every prompt edit. Detail: `{ prompt }`.
 * @fires avatar-generate - When the user asks to generate. Detail: `{ prompt }`.
 */
@customElement('avatar-prompt-generator')
export class AvatarPromptGenerator extends LitElement {
  @property({ type: String }) prompt = '';
  @property({ type: Boolean, attribute: 'processing' }) isProcessing = false;

  protected override createRenderRoot() {
    return this;
  }

  private handlePromptInput(e: CustomEvent<GaChangeDetail>) {
    e.stopPropagation();
    this.prompt = e.detail.value;
    this.dispatchEvent(
      new CustomEvent<AvatarPromptDetail>('avatar-prompt-change', {
        detail: { prompt: this.prompt },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private handleGenerate() {
    if (this.isProcessing || !this.prompt.trim()) return;
    this.dispatchEvent(
      new CustomEvent<AvatarPromptDetail>('avatar-generate', {
        detail: { prompt: this.prompt },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected override render() {
    return html`
      <div class="flex flex-col gap-4">
        <ga-field
          label="Generate with Nano Banana"
          multiline
          .rows="${4}"
          placeholder="A cinematic portrait of a cybernetic entity..."
          .value="${this.prompt}"
          @ga-change="${this.handlePromptInput}"
        ></ga-field>

        <ga-button
          variant="tonal"
          full-width
          label="Generate Image"
          loading-label="Generating..."
          ?loading="${this.isProcessing}"
          ?disabled="${this.isProcessing || !this.prompt.trim()}"
          @click="${this.handleGenerate}"
        ></ga-button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-prompt-generator': AvatarPromptGenerator;
  }
  interface HTMLElementEventMap {
    'avatar-prompt-change': CustomEvent<AvatarPromptDetail>;
    'avatar-generate': CustomEvent<AvatarPromptDetail>;
  }
}
