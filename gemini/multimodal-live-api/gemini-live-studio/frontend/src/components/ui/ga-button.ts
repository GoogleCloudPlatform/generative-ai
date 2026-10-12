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
import { renderIcon, type GaIconName } from './icons';

export type GaButtonVariant =
  'primary' | 'tonal' | 'pill' | 'danger' | 'danger-tonal' | 'ghost' | 'link';

export type GaButtonSize = 'sm' | 'md' | 'lg';

/**
 * Button (`<ga-button>`): CTAs, tonal actions, media pill toggles, and
 * destructive actions with consistent focus rings, loading and disabled states.
 *
 * - Toggle buttons (mic, camera, mute) set `toggle`; `active` is then exposed
 *   as `aria-pressed`.
 * - Icon-only buttons (no `label`) must set `accessible-label`.
 * - Listen for the native `click` event; it is suppressed while `disabled`
 *   or `loading`.
 */
@customElement('ga-button')
export class GaButton extends LitElement {
  @property({ type: String }) label = '';
  @property({ type: String, attribute: 'loading-label' }) loadingLabel = '';
  @property({ type: String, reflect: true }) variant: GaButtonVariant =
    'primary';
  @property({ type: String, reflect: true }) size: GaButtonSize = 'md';
  @property({ type: String }) icon?: GaIconName;
  @property({ type: String, attribute: 'trailing-icon' })
  trailingIcon?: GaIconName;
  @property({ type: Boolean, reflect: true }) disabled = false;
  @property({ type: Boolean, reflect: true }) loading = false;
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String, attribute: 'active-tone' }) activeTone:
    'primary' | 'danger' = 'primary';
  /** Exposes `active` as `aria-pressed` (for on/off toggle buttons). */
  @property({ type: Boolean }) toggle = false;
  /** Accessible name when the visible label is missing or ambiguous. */
  @property({ type: String, attribute: 'accessible-label' }) accessibleLabel =
    '';
  @property({ type: Boolean, attribute: 'ping-dot' }) pingDot = false;
  @property({ type: Boolean, attribute: 'full-width' }) fullWidth = false;
  @property({ type: String, attribute: 'button-type' }) buttonType:
    'button' | 'submit' | 'reset' = 'button';

  private readonly handleHostClick = (e: Event) => {
    if (this.disabled || this.loading) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  };

  override connectedCallback(): void {
    super.connectedCallback();
    this.addEventListener('click', this.handleHostClick, true);
  }

  override disconnectedCallback(): void {
    this.removeEventListener('click', this.handleHostClick, true);
    super.disconnectedCallback();
  }

  protected override createRenderRoot() {
    return this;
  }

  private variantClasses(): string {
    if (this.variant === 'pill') {
      if (this.active) {
        return this.activeTone === 'danger'
          ? 'bg-error text-on-error hover:bg-error-container hover:text-on-error-container ring-4 ring-error/20 rounded-full shadow-sm'
          : 'bg-primary text-on-primary ring-2 ring-primary/40 rounded-full shadow-sm';
      }
      return 'bg-surface-container-highest text-on-surface hover:bg-surface-container-high rounded-full shadow-sm';
    }

    switch (this.variant) {
      case 'primary':
        return this.size === 'lg'
          ? 'bg-primary text-on-primary shadow-lg shadow-primary/30 hover:bg-primary-hover rounded-full tracking-wide transform hover:-translate-y-0.5 hover:shadow-xl hover:shadow-primary/30 disabled:transform-none disabled:shadow-none'
          : 'bg-primary text-on-primary hover:bg-primary-hover rounded-xl shadow-sm';
      case 'tonal':
        return 'bg-surface-container-highest text-on-surface hover:bg-primary-soft hover:text-on-primary-soft rounded-xl shadow-sm';
      case 'danger':
        return 'bg-surface-container-highest text-on-surface hover:bg-error hover:text-on-error rounded-xl shadow-sm';
      case 'danger-tonal':
        return 'bg-surface-container-highest text-error hover:bg-error-container hover:text-on-error-container rounded-full shadow-sm';
      case 'ghost':
        return 'bg-transparent text-on-surface hover:bg-surface-container-highest rounded-xl';
      case 'link':
        return 'bg-transparent text-primary-text hover:underline rounded p-0 shadow-none';
    }
  }

  private sizeClasses(): string {
    if (this.variant === 'link') {
      return 'text-xs font-bold';
    }
    switch (this.size) {
      case 'sm':
        return 'px-3 py-1.5 text-xs font-semibold gap-1.5';
      case 'lg':
        return 'px-8 py-3 text-base font-bold gap-2';
      case 'md':
      default:
        return this.variant === 'pill' || this.variant === 'danger-tonal'
          ? 'px-4 py-2.5 text-sm font-bold gap-2'
          : 'px-6 py-2.5 text-sm font-bold gap-2';
    }
  }

  protected override render() {
    const isBusy = this.loading;
    const isDisabled = this.disabled || isBusy;
    const displayLabel =
      isBusy && this.loadingLabel ? this.loadingLabel : this.label;
    const iconSizeClass =
      this.size === 'lg' ? 'w-5 h-5 shrink-0' : 'w-4 h-4 shrink-0';

    return html`
      <button
        type="${this.buttonType}"
        ?disabled="${isDisabled}"
        aria-busy="${isBusy ? 'true' : 'false'}"
        aria-pressed="${this.toggle ? (this.active ? 'true' : 'false') : nothing}"
        aria-label="${this.accessibleLabel || nothing}"
        class="inline-flex items-center justify-center transition-all whitespace-nowrap shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
          this.fullWidth ? 'w-full' : ''
        } ${this.variantClasses()} ${this.sizeClasses()}"
      >
        ${
          isBusy
            ? renderIcon('spinner', iconSizeClass)
            : this.pingDot
              ? html`<span
                class="w-2 h-2 rounded-full bg-on-error animate-ping shrink-0"
              ></span>`
              : this.icon
                ? renderIcon(this.icon, iconSizeClass)
                : nothing
        }
        ${displayLabel ? html`<span>${displayLabel}</span>` : nothing}
        ${
          !isBusy && this.trailingIcon
            ? renderIcon(this.trailingIcon, iconSizeClass)
            : nothing
        }
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-button': GaButton;
  }
}
