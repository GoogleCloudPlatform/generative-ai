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
import { renderIcon, type GaIconName } from './icons';
import { uniqueId } from './ids';

/**
 * Checkbox with a label, optional description and icon (`<ga-checkbox>`).
 *
 * Uses a native `<input type="checkbox">` wrapped in its `<label>`, so the
 * whole card is clickable and the label is the accessible name; the
 * description is linked with `aria-describedby`.
 *
 * - `appearance="card"` (default): bordered card, used for feature toggles
 *   such as Google Search / Info Cards.
 * - `appearance="inline"`: plain row, for settings lists.
 *
 * @fires ga-change - When the user toggles it. Detail: `{ value, checked }`
 *   where `value` is `"true"` or `"false"`.
 */
@customElement('ga-checkbox')
export class GaCheckbox extends LitElement {
  /** Accessible label (required). */
  @property({ type: String }) label = '';
  @property({ type: String }) description = '';
  @property({ type: String }) icon?: GaIconName;
  @property({ type: Boolean, reflect: true }) checked = false;
  @property({ type: Boolean, reflect: true }) disabled = false;
  @property({ type: String, reflect: true }) appearance: 'card' | 'inline' =
    'card';

  private readonly controlId = uniqueId('ga-checkbox');

  protected override createRenderRoot() {
    return this;
  }

  private handleChange(e: Event) {
    this.checked = (e.target as HTMLInputElement).checked;
    this.dispatchEvent(
      new CustomEvent<GaChangeDetail>('ga-change', {
        detail: { value: String(this.checked), checked: this.checked },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected override render() {
    const id = this.controlId;
    const card = this.appearance === 'card';
    return html`
      <label
        class="flex items-center ${
          card
            ? 'justify-between gap-1 p-3 bg-surface-container-low rounded-xl border border-outline-variant/20 hover:bg-surface-container'
            : 'flex-row-reverse justify-end gap-3 py-1'
        } transition-colors ${
          this.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
        }"
      >
        <div class="flex items-center gap-2.5">
          ${
            this.icon
              ? html`<div
                class="w-7 h-7 rounded-full bg-primary-soft text-on-primary-soft flex items-center justify-center shrink-0"
                aria-hidden="true"
              >
                ${renderIcon(this.icon, 'w-4 h-4')}
              </div>`
              : nothing
          }
          <div class="${card ? 'text-xs' : 'text-sm'}">
            <div class="${card ? 'font-semibold' : ''} text-on-surface">${this.label}</div>
            ${
              this.description
                ? html`<div id="${id}-desc" class="text-[11px] text-on-surface-variant">
                  ${this.description}
                </div>`
                : nothing
            }
          </div>
        </div>
        <input
          id="${id}"
          type="checkbox"
          aria-describedby="${this.description ? `${id}-desc` : nothing}"
          .checked="${this.checked}"
          ?disabled="${this.disabled}"
          @change="${this.handleChange}"
          class="${card ? 'w-4 h-4' : 'w-5 h-5'} shrink-0 rounded accent-primary focus-visible:ring-2 focus-visible:ring-primary"
        />
      </label>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-checkbox': GaCheckbox;
  }
}
