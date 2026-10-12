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
import { customElement, property, state } from 'lit/decorators.js';
import {
  MAX_GROUNDING_CONTEXT_CHARS,
  MAX_SYSTEM_INSTRUCTION_CHARS,
} from '../../domain/presets';
import { resizeToMaxDimension } from '../../image-utils';
import { showToast, type GaChangeDetail } from '../../theme/events';
import { renderIcon } from '../ui/icons';
import '../ui/ga-badge';
import '../ui/ga-field';

export interface AvatarContextChangeDetail {
  systemInstruction: string;
  welcomeMessage: string;
  groundingContext: string;
}

/**
 * Domain component (`<avatar-context-drawer>`) encapsulating the collapsible
 * Persona, Greeting, & Reference Material grounding drawer (including `.txt/.md`
 * attachment and `/api/describe-image` vision context extraction).
 *
 * @fires avatar-context-change - When the user edits any field or attaches a
 *   file. Detail: `{ systemInstruction, welcomeMessage, groundingContext }`.
 */
@customElement('avatar-context-drawer')
export class AvatarContextDrawer extends LitElement {
  @property({ type: String, attribute: 'system-instruction' })
  systemInstruction = '';
  @property({ type: String, attribute: 'welcome-message' }) welcomeMessage = '';
  @property({ type: String, attribute: 'grounding-context' }) groundingContext =
    '';

  @state() private attachedFileName = '';
  @state() private isDescribingImage = false;

  protected override createRenderRoot() {
    return this;
  }

  private emitContextChange() {
    this.dispatchEvent(
      new CustomEvent<AvatarContextChangeDetail>('avatar-context-change', {
        detail: {
          systemInstruction: this.systemInstruction,
          welcomeMessage: this.welcomeMessage,
          groundingContext: this.groundingContext,
        },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private clampGroundingContext(nextText: string): string {
    if (nextText.length > MAX_GROUNDING_CONTEXT_CHARS) {
      showToast(
        `Grounding context truncated to ${MAX_GROUNDING_CONTEXT_CHARS.toLocaleString()} characters.`,
        'danger',
      );
      return nextText.slice(0, MAX_GROUNDING_CONTEXT_CHARS);
    }
    return nextText;
  }

  private clampSystemInstruction(nextText: string): string {
    if (nextText.length > MAX_SYSTEM_INSTRUCTION_CHARS) {
      showToast(
        `System instruction truncated to ${MAX_SYSTEM_INSTRUCTION_CHARS.toLocaleString()} characters.`,
        'danger',
      );
      return nextText.slice(0, MAX_SYSTEM_INSTRUCTION_CHARS);
    }
    return nextText;
  }

  private handleTextFileAttach(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = (reader.result as string) || '';
      const added = `[Attached File (${file.name})]:\n${text}`;
      const combined = this.groundingContext
        ? `${this.groundingContext}\n\n${added}`
        : added;
      this.groundingContext = this.clampGroundingContext(combined);
      this.attachedFileName = file.name;
      input.value = '';
      this.emitContextChange();
    };
    reader.onerror = () => {
      showToast('Failed to read attached text file.', 'danger');
      input.value = '';
    };
    reader.readAsText(file);
  }

  private async handleImageForContextUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (file.size > 8 * 1024 * 1024) {
      showToast('Image size exceeds 8MB limit.', 'danger');
      input.value = '';
      return;
    }

    this.isDescribingImage = true;
    try {
      const reader = new FileReader();
      const base64DataUrl = await new Promise<string>((resolve, reject) => {
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
      const resized = await resizeToMaxDimension(base64DataUrl, 1024);
      const resp = await fetch('/api/describe-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: resized }),
      });
      if (!resp.ok) {
        const errText = (await resp.text()).trim();
        throw new Error(errText || 'Failed to analyze image');
      }
      const data = await resp.json();
      if (data.description) {
        const added = `[Image Reference (${file.name})]: ${data.description}`;
        const combined = this.groundingContext
          ? `${this.groundingContext}\n\n${added}`
          : added;
        this.groundingContext = this.clampGroundingContext(combined);
        this.emitContextChange();
      }
    } catch (err) {
      console.error('Failed to describe image:', err);
      const msg =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to generate image description.';
      showToast(msg, 'danger');
    } finally {
      this.isDescribingImage = false;
      input.value = '';
    }
  }

  protected override render() {
    return html`
      <details
        class="group bg-surface-container-low/50 rounded-xl border border-outline-variant/20 p-4"
      >
        <summary
          class="cursor-pointer font-semibold text-sm text-on-surface flex items-center justify-between list-none"
        >
          <span>Persona, Greeting &amp; Reference Material</span>
          ${renderIcon(
            'chevron-down',
            'w-4 h-4 text-outline transition-transform group-open:rotate-180',
          )}
        </summary>
        <div class="mt-4 flex flex-col gap-4">
          <ga-field
            label="System Instruction (optional)"
            label-size="xs"
            surface="container"
            size="sm"
            multiline
            .rows="${2}"
            .maxLength="${MAX_SYSTEM_INSTRUCTION_CHARS}"
            placeholder="You are a helpful assistant..."
            .value="${this.systemInstruction}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) => {
              e.stopPropagation();
              this.systemInstruction = this.clampSystemInstruction(
                e.detail.value,
              );
              this.emitContextChange();
            }}"
          ></ga-field>

          <ga-field
            label="Welcome Message (optional)"
            label-size="xs"
            surface="container"
            size="sm"
            placeholder="What Gemini says the moment the session connects"
            .value="${this.welcomeMessage}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) => {
              e.stopPropagation();
              this.welcomeMessage = e.detail.value;
              this.emitContextChange();
            }}"
          ></ga-field>

          <div>
            <ga-field
              label="Reference Material / Grounding Context (optional)"
              label-size="xs"
              surface="container"
              size="sm"
              multiline
              .rows="${3}"
              .maxLength="${MAX_GROUNDING_CONTEXT_CHARS}"
              placeholder="Paste reference notes, docs, or attach a text file or image below..."
              .value="${this.groundingContext}"
              @ga-change="${(e: CustomEvent<GaChangeDetail>) => {
                e.stopPropagation();
                this.groundingContext = this.clampGroundingContext(
                  e.detail.value,
                );
                this.emitContextChange();
              }}"
            ></ga-field>

            <div
              class="mt-2 flex flex-wrap items-center justify-between gap-2"
            >
              <div class="flex flex-wrap items-center gap-2">
                <label
                  class="cursor-pointer px-3 py-1.5 rounded-lg bg-surface-container-highest hover:bg-primary-soft hover:text-on-primary-soft text-xs font-semibold text-on-surface transition-colors flex items-center gap-1.5"
                >
                  ${renderIcon('paperclip', 'w-3.5 h-3.5')}
                  Attach .txt/.md
                  <input
                    type="file"
                    accept=".txt,.md,.json,.csv"
                    class="hidden"
                    @change="${this.handleTextFileAttach}"
                  />
                </label>

                <label
                  class="cursor-pointer px-3 py-1.5 rounded-lg bg-surface-container-highest hover:bg-primary-soft hover:text-on-primary-soft text-xs font-semibold text-on-surface transition-colors flex items-center gap-1.5 ${
                    this.isDescribingImage
                      ? 'opacity-50 pointer-events-none'
                      : ''
                  }"
                >
                  ${renderIcon('image', 'w-3.5 h-3.5')}
                  ${
                    this.isDescribingImage
                      ? 'Analyzing Image...'
                      : 'Describe Image for Context'
                  }
                  <input
                    type="file"
                    accept="image/*"
                    class="hidden"
                    @change="${this.handleImageForContextUpload}"
                  />
                </label>

                ${
                  this.attachedFileName
                    ? html`<ga-badge
                      label="${this.attachedFileName}"
                      tone="primary"
                    ></ga-badge>`
                    : nothing
                }
              </div>
              <span class="text-[11px] text-on-surface-variant">
                ${this.groundingContext.length.toLocaleString()} /
                ${MAX_GROUNDING_CONTEXT_CHARS.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </details>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-context-drawer': AvatarContextDrawer;
  }
  interface HTMLElementEventMap {
    'avatar-context-change': CustomEvent<AvatarContextChangeDetail>;
  }
}
