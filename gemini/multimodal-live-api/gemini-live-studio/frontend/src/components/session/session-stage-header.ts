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
/** User intents emitted by shared session components as `session-action`. */
import { LitElement, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import '../ui/ga-badge';
import '../ui/ga-button';
import { sessionActionEvent } from './session-events';

/**
 * Stage header (`<session-stage-header>`) shared by the avatar video stage
 * and the live audio stage: connection status, voice, and the serving model.
 *
 * With `mute-toggle`, the voice label is a toggle button that mutes the
 * assistant's audio.
 *
 * @fires session-action - With `mute-toggle`, when the voice button is
 *   pressed. Detail: `{ action: 'toggle-mute' }`.
 */
@customElement('session-stage-header')
export class SessionStageHeader extends LitElement {
  @property({ type: String }) status = 'Connecting...';
  @property({ type: String, attribute: 'voice-name' }) voiceName = '';
  @property({ type: String, attribute: 'session-model' }) sessionModel = '';
  @property({ type: String, attribute: 'session-location' }) sessionLocation =
    '';
  @property({ type: Boolean, attribute: 'mute-toggle' }) muteToggle = false;
  @property({ type: Boolean }) muted = false;

  protected override createRenderRoot() {
    return this;
  }

  protected override render() {
    const modelLabel = this.sessionModel
      ? `${this.sessionModel}${this.sessionLocation ? ` (${this.sessionLocation})` : ''}`
      : '';
    return html`
      <div
        class="px-6 py-4 flex items-center justify-between border-b border-outline-variant/20 bg-surface shrink-0 gap-2 flex-wrap"
      >
        <ga-status-dot .status="${this.status}"></ga-status-dot>
        <div class="flex items-center gap-2 text-sm font-mono text-on-surface-variant">
          ${
            this.muteToggle
              ? html`<ga-button
                variant="ghost"
                size="sm"
                toggle
                ?active="${this.muted}"
                icon="${this.muted ? 'volume-off' : 'volume-up'}"
                label="${this.muted ? 'Muted' : `${this.voiceName} Voice`}"
                @click="${() => this.dispatchEvent(sessionActionEvent('toggle-mute'))}"
              ></ga-button>`
              : html`<span>${this.voiceName} Voice</span>`
          }
          ${
            modelLabel
              ? html`<ga-badge
                label="${modelLabel}"
                tone="neutral"
                badge-title="Serving Live Model &amp; Location"
              ></ga-badge>`
              : nothing
          }
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'session-stage-header': SessionStageHeader;
  }
}
