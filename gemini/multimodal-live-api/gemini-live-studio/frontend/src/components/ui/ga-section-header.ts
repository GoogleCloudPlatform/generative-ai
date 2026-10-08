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
import './ga-button';

/**
 * Heading + subheading block (`<ga-section-header>`) for page cards
 * (`size="page"`, an `<h2>`) and settings sections (`size="section"`, an
 * `<h3>`), with an optional trailing link-style action.
 *
 * @fires ga-action - When the action link is clicked. No detail.
 */
@customElement('ga-section-header')
export class GaSectionHeader extends LitElement {
  @property({ type: String }) heading = '';
  @property({ type: String }) subheading = '';
  @property({ type: String, reflect: true }) size: 'page' | 'section' =
    'section';
  /** Label of the optional trailing action (e.g. "Reset to defaults"). */
  @property({ type: String, attribute: 'action-label' }) actionLabel = '';

  protected override createRenderRoot() {
    return this;
  }

  private emitAction() {
    this.dispatchEvent(
      new CustomEvent('ga-action', { bubbles: true, composed: true }),
    );
  }

  protected override render() {
    const page = this.size === 'page';
    // Heading and action share the first row; the subheading spans the full
    // width below so long descriptions are not squeezed by the action.
    return html`
      <div class="flex items-center justify-between gap-4">
        ${
          page
            ? html`<h2 class="text-3xl font-bold text-on-surface tracking-tight mb-2">${this.heading}</h2>`
            : html`<h3 class="text-xl font-semibold text-on-surface">${this.heading}</h3>`
        }
        ${
          this.actionLabel
            ? html`<ga-button variant="link" label="${this.actionLabel}" @click="${this.emitAction}"></ga-button>`
            : nothing
        }
      </div>
      ${
        this.subheading
          ? html`<p class="${page ? 'text-on-surface-variant text-sm' : 'text-sm text-on-surface-variant mt-1'}">
            ${this.subheading}
          </p>`
          : nothing
      }
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-section-header': GaSectionHeader;
  }
  interface HTMLElementEventMap {
    'ga-action': CustomEvent<void>;
  }
}
