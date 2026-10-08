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
import { customElement, state } from 'lit/decorators.js';
import type { GaToastDetail } from '../../theme/events';
import type { GaTone } from '../../theme/tokens';
import { renderIcon } from './icons';

interface ToastItem {
  id: number;
  message: string;
  tone: GaTone;
}

/**
 * Accessible status toast region (`<ga-toast-region>`).
 *
 * Listens for `ga-toast` events (dispatched via `showToast()`) and renders
 * non-blocking `role="status"` notifications instead of browser `alert()`s.
 */
@customElement('ga-toast-region')
export class GaToastRegion extends LitElement {
  @state() private toasts: ToastItem[] = [];
  private nextId = 1;

  private readonly handleToast = (e: Event) => {
    const detail = (e as CustomEvent<GaToastDetail>).detail;
    if (!detail?.message) return;
    const id = this.nextId++;
    const item: ToastItem = {
      id,
      message: detail.message,
      tone: detail.tone ?? 'primary',
    };
    this.toasts = [...this.toasts, item];
    const duration = detail.durationMs ?? 3200;
    setTimeout(() => this.dismiss(id), duration);
  };

  override connectedCallback(): void {
    super.connectedCallback();
    globalThis.window?.addEventListener('ga-toast', this.handleToast);
  }

  override disconnectedCallback(): void {
    globalThis.window?.removeEventListener('ga-toast', this.handleToast);
    super.disconnectedCallback();
  }

  protected override createRenderRoot() {
    return this;
  }

  private dismiss(id: number) {
    this.toasts = this.toasts.filter((t) => t.id !== id);
  }

  private toneClasses(tone: GaTone): string {
    switch (tone) {
      case 'danger':
        return 'bg-error-container text-on-error-container border-error/30';
      case 'success':
        return 'bg-success-container text-on-success-container border-success/30';
      case 'primary':
      case 'neutral':
      default:
        return 'bg-inverse-surface text-inverse-on-surface border-outline-variant/20';
    }
  }

  private renderToast(t: ToastItem) {
    return html`
      <div
        class="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all ${this.toneClasses(
          t.tone,
        )}"
      >
        ${renderIcon(
          t.tone === 'danger' ? 'alert-circle' : 'check-circle',
          'w-4 h-4 shrink-0',
        )}
        <span class="flex-1">${t.message}</span>
        <button
          type="button"
          aria-label="Dismiss notification"
          @click="${() => this.dismiss(t.id)}"
          class="opacity-70 hover:opacity-100 p-1 rounded"
        >
          ${renderIcon('close', 'w-3.5 h-3.5')}
        </button>
      </div>
    `;
  }

  // Both live regions are always in the DOM: screen readers only announce
  // content added to a region that already exists. Danger toasts go to the
  // assertive region, everything else to the polite one.
  protected override render() {
    const alerts = this.toasts.filter((t) => t.tone === 'danger');
    const statuses = this.toasts.filter((t) => t.tone !== 'danger');
    return html`
      <div
        class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm pointer-events-none"
      >
        <div role="alert" aria-live="assertive" class="flex flex-col gap-2">
          ${alerts.map((t) => this.renderToast(t))}
        </div>
        <div role="status" aria-live="polite" class="flex flex-col gap-2">
          ${statuses.map((t) => this.renderToast(t))}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ga-toast-region': GaToastRegion;
  }
}
