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
import { ifDefined } from 'lit/directives/if-defined.js';
import type { GaChangeDetail } from '../../theme/events';
import { uniqueId } from './ids';

/**
 * Text, number or multi-line field (`<ga-field>`).
 *
 * The label is a real `<label for>` linked to the control, and supporting
 * text, the character counter and `error-text` are linked with
 * `aria-describedby`. Always set `label`; use `hide-label` when the visual
 * design has no visible label.
 *
 * @fires ga-change - On every user edit. Detail: `{ value }`.
 */
@customElement('ga-field')
export class GaField extends LitElement {
  /** Accessible label (required). */
  @property({ type: String }) label = '';
  /** Visually hide the label while keeping it as the accessible name. */
  @property({ type: Boolean, attribute: 'hide-label' }) hideLabel = false;
  @property({ type: String, attribute: 'label-size' }) labelSize: 'xs' | 'sm' =
    'sm';
  @property({ type: String }) value = '';
  @property({ type: String }) placeholder = '';
  @property({ type: String }) type: 'text' | 'number' = 'text';
  @property({ type: Boolean }) multiline = false;
  @property({ type: Number }) rows = 3;
  /** Maximum length in characters; enforced on input and shown as a counter. */
  @property({ type: Number, attribute: 'max-length' }) maxLength = 0;
  @property({ type: String, attribute: 'supporting-text' }) supportingText = '';
  /** Error message; marks the control `aria-invalid` when set. */
  @property({ type: String, attribute: 'error-text' }) errorText = '';
  @property({ type: String }) surface: 'low' | 'container' = 'low';
  @property({ type: String }) size: 'sm' | 'md' = 'md';
  @property({ type: Number }) min?: number;
  @property({ type: Number }) max?: number;
  @property({ type: Number }) step?: number;
  @property({ type: Boolean }) disabled = false;

  private readonly controlId = uniqueId('ga-field');

  protected override createRenderRoot() {
    return this;
  }

  private handleInput(e: Event) {
    const nextValue = (e.target as HTMLInputElement | HTMLTextAreaElement)
      .value;
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
    const id = this.controlId;
    const bgClass =
      this.surface === 'container'
        ? 'bg-surface-container'
        : 'bg-surface-container-low';
    const padClass =
      this.size === 'sm' ? 'px-3 py-2 text-sm' : 'px-4 py-3 text-sm';
    const labelClass = this.hideLabel
      ? 'sr-only'
      : this.labelSize === 'xs'
        ? 'block text-xs font-semibold text-on-surface'
        : 'block text-sm font-semibold text-on-surface';
    const invalid = this.errorText !== '';
    const describedBy =
      [
        this.supportingText ? `${id}-support` : '',
        this.maxLength > 0 ? `${id}-count` : '',
        invalid ? `${id}-error` : '',
      ]
        .filter(Boolean)
        .join(' ') || undefined;
    const ringClass = invalid ? 'ring-2 ring-error' : '';
    const maxLength = this.maxLength > 0 ? this.maxLength : undefined;

    return html`
      <div class="flex flex-col gap-1.5 w-full">
        ${
          this.label
            ? html`<label for="${id}" class="${labelClass}">${this.label}</label>`
            : nothing
        }
        ${
          this.multiline
            ? html`
              <textarea
                id="${id}"
                rows="${this.rows}"
                placeholder="${this.placeholder}"
                maxlength="${ifDefined(maxLength)}"
                aria-describedby="${ifDefined(describedBy)}"
                aria-invalid="${invalid ? 'true' : nothing}"
                ?disabled="${this.disabled}"
                .value="${this.value}"
                @input="${this.handleInput}"
                class="w-full ${bgClass} border-none rounded-xl ${padClass} ${ringClass} text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest resize-none transition-all"
              ></textarea>
            `
            : html`
              <input
                id="${id}"
                type="${this.type}"
                placeholder="${this.placeholder}"
                maxlength="${ifDefined(maxLength)}"
                min="${ifDefined(this.min)}"
                max="${ifDefined(this.max)}"
                step="${ifDefined(this.step)}"
                aria-describedby="${ifDefined(describedBy)}"
                aria-invalid="${invalid ? 'true' : nothing}"
                ?disabled="${this.disabled}"
                .value="${this.value}"
                @input="${this.handleInput}"
                class="w-full ${bgClass} border-none rounded-xl ${padClass} ${ringClass} text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all"
              />
            `
        }
        ${
          invalid
            ? html`<span id="${id}-error" class="text-xs text-error"
              >${this.errorText}</span
            >`
            : nothing
        }
        ${
          this.supportingText || this.maxLength > 0
            ? html`
              <div class="flex items-center justify-between gap-2">
                ${
                  this.supportingText
                    ? html`<span
                      id="${id}-support"
                      class="text-xs text-on-surface-variant"
                      >${this.supportingText}</span
                    >`
                    : html`<span></span>`
                }
                ${
                  this.maxLength > 0
                    ? html`<span
                      id="${id}-count"
                      class="text-[11px] text-on-surface-variant shrink-0"
                    >
                      ${this.value.length.toLocaleString()} /
                      ${this.maxLength.toLocaleString()}
                      <span class="sr-only">characters</span>
                    </span>`
                    : nothing
                }
              </div>
            `
            : nothing
        }
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-field': GaField;
  }
}
