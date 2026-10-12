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
import { RovingFocusController } from '../../controllers/roving-focus-controller';

export interface GaSegmentOption<T extends string = string> {
  value: T;
  label: string;
  hidden?: boolean;
}

/**
 * Segmented tab control (`<ga-segmented-control>`): a `role="tablist"` with
 * roving focus (Left/Right, mirrored in RTL, Home/End). Moving with the
 * keyboard selects the tab.
 *
 * @fires ga-change - When the user selects a different segment. Detail: `{ value }`.
 */
@customElement('ga-segmented-control')
export class GaSegmentedControl extends LitElement {
  @property({ attribute: false }) options: readonly GaSegmentOption[] = [];
  @property({ type: String }) value = '';
  @property({ type: String, attribute: 'aria-label' })
  override ariaLabel: string | null = 'Options';

  private readonly roving = new RovingFocusController(this, {
    orientation: 'horizontal',
    items: () => [...this.querySelectorAll<HTMLElement>('button[role="tab"]')],
    onMove: (item) => this.selectValue(item.dataset.value ?? ''),
  });

  protected override createRenderRoot() {
    return this;
  }

  private visibleOptions(): readonly GaSegmentOption[] {
    return this.options.filter((o) => !o.hidden);
  }

  private selectValue(nextValue: string) {
    if (nextValue === this.value) return;
    this.value = nextValue;
    this.dispatchEvent(
      new CustomEvent<GaChangeDetail>('ga-change', {
        detail: { value: nextValue },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected override updated(): void {
    this.roving.sync(
      this.visibleOptions().findIndex((o) => o.value === this.value),
    );
  }

  protected override render() {
    const visible = this.visibleOptions();
    if (visible.length === 0) return nothing;

    return html`
      <div
        role="tablist"
        aria-label="${this.ariaLabel || 'Options'}"
        class="flex bg-surface-container p-1 rounded-xl gap-1 w-full"
      >
        ${visible.map((opt) => {
          const isSelected = opt.value === this.value;
          return html`
            <button
              type="button"
              role="tab"
              aria-selected="${isSelected ? 'true' : 'false'}"
              data-value="${opt.value}"
              @click="${() => this.selectValue(opt.value)}"
              class="flex-1 py-2 px-3 text-sm font-semibold rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                isSelected
                  ? 'bg-surface-container-lowest text-primary-text shadow-sm'
                  : 'text-on-surface hover:bg-surface-container-highest'
              }"
            >
              ${opt.label}
            </button>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-segmented-control': GaSegmentedControl;
  }
}
