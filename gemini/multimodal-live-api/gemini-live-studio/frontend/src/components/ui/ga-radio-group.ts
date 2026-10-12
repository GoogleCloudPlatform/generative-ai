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
import type { GaChangeDetail } from '../../theme/events';
import { RovingFocusController } from '../../controllers/roving-focus-controller';
import './ga-badge';
import { uniqueId } from './ids';

export interface GaRadioOption<T extends string = string> {
  value: T;
  label: string;
  description?: string;
  /** Small badge next to the label (`card` appearance). */
  badge?: string;
  /** Leading image (`tile` appearance), e.g. an avatar thumbnail. */
  imageSrc?: string;
  /** Short text (e.g. an initial) shown instead if `imageSrc` fails to load. */
  imageFallbackText?: string;
  disabled?: boolean;
}

export type GaRadioAppearance = 'chip' | 'tile' | 'card';

/**
 * Single-choice group (`<ga-radio-group>`): `role="radiogroup"` with
 * `role="radio"` options and roving focus. Arrow keys move and select,
 * Home/End jump, Tab leaves the group.
 *
 * Appearances:
 * - `chip`: compact pills that wrap (persona presets).
 * - `tile`: image + label in a grid (avatar presets).
 * - `card`: title, optional badge and description (processing modes).
 *
 * Grid/flex layout can be overridden with `layout-class`.
 *
 * @fires ga-change - When the user selects an option. Detail: `{ value }`.
 */
@customElement('ga-radio-group')
export class GaRadioGroup extends LitElement {
  /** Accessible group label (required). */
  @property({ type: String }) label = '';
  @property({ type: Boolean, attribute: 'hide-label' }) hideLabel = false;
  /** `eyebrow` renders the small uppercase label style. */
  @property({ type: String, attribute: 'label-style' }) labelStyle:
    'default' | 'eyebrow' = 'default';
  @property({ type: String }) value = '';
  @property({ attribute: false }) options: readonly GaRadioOption[] = [];
  @property({ type: String, reflect: true }) appearance: GaRadioAppearance =
    'chip';
  @property({ type: String, attribute: 'layout-class' }) layoutClass = '';
  @property({ type: Boolean, reflect: true }) disabled = false;

  /** Image URLs that failed to load; their fallback text is shown instead. */
  @state() private failedImages: ReadonlySet<string> = new Set();

  private readonly labelId = uniqueId('ga-radio-group');

  private readonly roving = new RovingFocusController(this, {
    items: () => this.radios(),
    onMove: (item) => this.select(item.dataset.value ?? ''),
  });

  protected override createRenderRoot() {
    return this;
  }

  private radios(): HTMLElement[] {
    return [
      ...this.querySelectorAll<HTMLElement>(
        '[role="radio"]:not([aria-disabled="true"])',
      ),
    ];
  }

  private select(value: string) {
    if (this.disabled || value === this.value) return;
    this.value = value;
    this.dispatchEvent(
      new CustomEvent<GaChangeDetail>('ga-change', {
        detail: { value },
        bubbles: true,
        composed: true,
      }),
    );
  }

  protected override updated(): void {
    this.roving.sync(
      this.radios().findIndex((r) => r.dataset.value === this.value),
    );
  }

  private handleImageError(src: string) {
    this.failedImages = new Set([...this.failedImages, src]);
  }

  private optionClasses(selected: boolean): string {
    const focus =
      'transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary aria-disabled:opacity-50 aria-disabled:cursor-not-allowed';
    switch (this.appearance) {
      case 'tile':
        return `flex items-center gap-3 p-2 rounded-xl border ${focus} ${
          selected
            ? 'border-primary bg-primary-soft text-on-primary-soft shadow-sm'
            : 'border-outline-variant/30 hover:border-outline hover:bg-surface-container-low text-on-surface'
        }`;
      case 'card':
        return `flex flex-col items-start gap-1 p-3 rounded-xl border text-left ${focus} ${
          selected
            ? 'border-2 border-primary bg-primary-soft/40 text-on-surface shadow-sm'
            : 'border-outline-variant/40 bg-surface-container-low hover:bg-surface-container-high text-on-surface'
        }`;
      case 'chip':
      default:
        return `px-3 py-1.5 rounded-full text-xs font-semibold border ${focus} ${
          selected
            ? 'border-primary bg-primary text-on-primary shadow-sm'
            : 'border-outline-variant/30 bg-surface-container-low text-on-surface hover:bg-surface-container-high'
        }`;
    }
  }

  private renderContent(opt: GaRadioOption) {
    switch (this.appearance) {
      case 'tile':
        return html`
          <span
            class="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center overflow-hidden flex-shrink-0"
          >
            ${
              opt.imageSrc && !this.failedImages.has(opt.imageSrc)
                ? html`<img
                  src="${opt.imageSrc}"
                  alt=""
                  loading="lazy"
                  class="w-full h-full object-cover object-top"
                  @error="${() => this.handleImageError(opt.imageSrc!)}"
                />`
                : html`<span aria-hidden="true" class="font-semibold text-on-surface-variant"
                  >${opt.imageFallbackText ?? ''}</span
                >`
            }
          </span>
          <span class="font-medium">${opt.label}</span>
        `;
      case 'card':
        return html`
          <span class="flex items-center justify-between w-full text-xs font-bold">
            <span>${opt.label}</span>
            ${
              opt.badge
                ? html`<ga-badge label="${opt.badge}" tone="primary-solid" uppercase></ga-badge>`
                : nothing
            }
          </span>
          ${
            opt.description
              ? html`<span class="text-[11px] text-on-surface-variant leading-snug"
                >${opt.description}</span
              >`
              : nothing
          }
        `;
      case 'chip':
      default:
        return opt.label;
    }
  }

  protected override render() {
    const defaultLayout =
      this.appearance === 'chip'
        ? 'flex flex-wrap gap-2'
        : this.appearance === 'tile'
          ? 'grid grid-cols-2 gap-3'
          : 'grid grid-cols-1 sm:grid-cols-3 gap-2';
    const labelClass = this.hideLabel
      ? 'sr-only'
      : this.labelStyle === 'eyebrow'
        ? 'block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2'
        : 'block text-sm font-semibold text-on-surface mb-3';
    return html`
      <div id="${this.labelId}" class="${labelClass}">${this.label}</div>
      <div
        role="radiogroup"
        aria-labelledby="${this.labelId}"
        aria-disabled="${this.disabled ? 'true' : nothing}"
        class="${this.layoutClass || defaultLayout}"
      >
        ${this.options.map((opt) => {
          const selected = opt.value === this.value;
          const disabled = this.disabled || !!opt.disabled;
          return html`
            <div
              role="radio"
              aria-checked="${selected ? 'true' : 'false'}"
              aria-disabled="${disabled ? 'true' : nothing}"
              data-value="${opt.value}"
              tabindex="-1"
              class="cursor-pointer select-none ${this.optionClasses(selected)}"
              @click="${() => !disabled && this.select(opt.value)}"
              @keydown="${(e: KeyboardEvent) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault();
                  if (!disabled) this.select(opt.value);
                }
              }}"
            >
              ${this.renderContent(opt)}
            </div>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-radio-group': GaRadioGroup;
  }
}
