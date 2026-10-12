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
import { customElement, property } from 'lit/decorators.js';
import type { GaChangeDetail } from '../../theme/events';
import { renderIcon } from './icons';
import { uniqueId } from './ids';

export interface GaSelectOption {
  value: string;
  label: string;
}

/**
 * Select dropdown (`<ga-select>`) with a native `<select>` for full keyboard
 * and screen-reader support. The label is linked with `<label for>` and the
 * supporting text with `aria-describedby`. Always set `label`; use
 * `hide-label` when the design has no visible label.
 *
 * @fires ga-change - When the user picks an option. Detail: `{ value }`.
 */
@customElement('ga-select')
export class GaSelect extends LitElement {
  /** Accessible label (required). */
  @property({ type: String }) label = '';
  /** Visually hide the label while keeping it as the accessible name. */
  @property({ type: Boolean, attribute: 'hide-label' }) hideLabel = false;
  @property({ type: String }) value = '';
  @property({ attribute: false }) options: readonly GaSelectOption[] = [];
  @property({ type: String, attribute: 'supporting-text' }) supportingText = '';
  @property({ type: String }) surface: 'low' | 'container' = 'low';
  @property({ type: String }) size: 'sm' | 'md' = 'md';
  @property({ type: Boolean }) disabled = false;

  private readonly controlId = uniqueId('ga-select');

  protected override createRenderRoot() {
    return this;
  }

  private handleChange(e: Event) {
    const nextValue = (e.target as HTMLSelectElement).value;
    this.value = nextValue;
    this.dispatchEvent(
      new CustomEvent<GaChangeDetail>('ga-change', {
        detail: { value: nextValue },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected override render() {
    const bgClass =
      this.surface === 'container'
        ? 'bg-surface-container'
        : 'bg-surface-container-low';
    const sizeClass =
      this.size === 'sm' ? 'px-3 py-2 text-xs' : 'px-4 py-3 text-sm';

    return html`
      <div class="flex flex-col gap-1.5 w-full">
        ${
          this.label
            ? html`<label
              for="${this.controlId}"
              class="${
                this.hideLabel
                  ? 'sr-only'
                  : 'block text-sm font-semibold text-on-surface'
              }"
              >${this.label}</label
            >`
            : nothing
        }
        <div class="relative">
          <select
            id="${this.controlId}"
            aria-describedby="${
              this.supportingText ? `${this.controlId}-support` : nothing
            }"
            ?disabled="${this.disabled}"
            .value="${this.value}"
            @change="${this.handleChange}"
            class="w-full appearance-none ${bgClass} border-none rounded-xl ${sizeClass} pr-10 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all disabled:opacity-50"
          >
            ${this.options.map(
              (opt) => html`
                <option
                  value="${opt.value}"
                  ?selected="${opt.value === this.value}"
                >
                  ${opt.label}
                </option>
              `,
            )}
          </select>
          <div
            class="absolute inset-y-0 right-4 flex items-center pointer-events-none text-outline"
          >
            ${renderIcon('chevron-down', 'w-4 h-4')}
          </div>
        </div>
        ${
          this.supportingText
            ? html`<span
              id="${this.controlId}-support"
              class="text-xs text-on-surface-variant"
              >${this.supportingText}</span
            >`
            : nothing
        }
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-select': GaSelect;
  }
}
