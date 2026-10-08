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

export type GaBadgeTone =
  'neutral' | 'primary' | 'primary-solid' | 'success' | 'danger';

/**
 * Standardized pill/chip badge (`<ga-badge>`).
 */
@customElement('ga-badge')
export class GaBadge extends LitElement {
  @property({ type: String }) label = '';
  @property({ type: String }) tone: GaBadgeTone = 'neutral';
  @property({ type: Boolean }) pill = false;
  @property({ type: Boolean }) uppercase = false;
  @property({ type: String, attribute: 'badge-title' }) badgeTitle = '';

  protected override createRenderRoot() {
    return this;
  }

  private toneClasses(): string {
    switch (this.tone) {
      case 'primary':
        return 'bg-primary-soft text-on-primary-soft';
      case 'primary-solid':
        return 'bg-primary text-on-primary';
      case 'success':
        return 'bg-success-container text-on-success-container';
      case 'danger':
        return 'bg-error-container text-on-error-container';
      case 'neutral':
      default:
        return 'bg-surface-container-highest text-on-surface-variant';
    }
  }

  protected override render() {
    if (!this.label) return nothing;
    return html`
      <span
        title="${this.badgeTitle || nothing}"
        class="inline-flex items-center px-2 py-0.5 text-xs font-medium ${
          this.pill ? 'rounded-full text-[11px]' : 'rounded-md'
        } ${
          this.uppercase ? 'uppercase text-[10px] font-bold px-1.5' : ''
        } ${this.toneClasses()}"
      >
        ${this.label}
      </span>
    `;
  }
}

/**
 * Standardized connection status indicator (`<ga-status-dot>`).
 */
@customElement('ga-status-dot')
export class GaStatusDot extends LitElement {
  @property({ type: String }) status = 'Connecting...';

  protected override createRenderRoot() {
    return this;
  }

  protected override render() {
    const isConnected = this.status === 'Connected';
    return html`
      <div
        role="status"
        aria-live="polite"
        class="inline-flex items-center gap-3"
      >
        <div
          class="w-3 h-3 rounded-full transition-colors ${
            isConnected
              ? 'bg-success shadow-[0_0_8px] shadow-success/50'
              : 'bg-error'
          }"
        ></div>
        <span class="font-semibold text-on-surface">${this.status}</span>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-badge': GaBadge;
    'ga-status-dot': GaStatusDot;
  }
}
