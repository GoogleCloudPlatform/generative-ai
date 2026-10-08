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
import { customElement, property } from 'lit/decorators.js';
import { renderIcon } from '../ui/icons';
import '../ui/ga-button';
import {
  sessionActionEvent,
  type SessionAction,
  type SessionSendTextDetail,
} from './session-events';

/**
 * Session controls (`<session-control-bar>`) shared by avatar and live
 * sessions: a message input plus camera, screen-share, end-session and mic
 * buttons. The media buttons are toggles (`aria-pressed`).
 *
 * @fires session-send-text - When the user submits a message. Detail: `{ text }`.
 * @fires session-action - When a control is pressed. Detail: `{ action }`, one of
 *   `toggle-camera`, `toggle-screen`, `toggle-mic`, `end-session`.
 */
@customElement('session-control-bar')
export class SessionControlBar extends LitElement {
  @property({ type: Boolean, attribute: 'camera-active' }) cameraActive = false;
  @property({ type: Boolean, attribute: 'screen-share-active' })
  screenShareActive = false;
  @property({ type: Boolean }) recording = false;
  @property({ type: Boolean }) terminating = false;

  protected override createRenderRoot() {
    return this;
  }

  private handleTextSubmit(e: KeyboardEvent) {
    if (e.key !== 'Enter' || e.isComposing) return;
    const input = e.target as HTMLInputElement;
    const text = input.value.trim();
    if (!text) return;
    this.dispatchEvent(
      new CustomEvent<SessionSendTextDetail>('session-send-text', {
        detail: { text },
        bubbles: true,
        composed: true,
      }),
    );
    input.value = '';
  }

  private emit(action: SessionAction) {
    this.dispatchEvent(sessionActionEvent(action));
  }

  protected override render() {
    return html`
      <div
        class="p-4 sm:p-5 bg-surface border-t border-outline-variant/20 flex flex-col gap-3 shrink-0"
      >
        <div class="w-full relative">
          <input
            type="text"
            aria-label="Message to Gemini"
            placeholder="Type a message to Gemini..."
            @keydown="${this.handleTextSubmit}"
            class="w-full bg-surface-container-low border-none rounded-full pl-5 pr-12 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:bg-surface-container-lowest transition-all placeholder:text-outline-variant"
          />
          <div
            class="absolute inset-y-0 right-4 flex items-center pointer-events-none text-outline"
          >
            ${renderIcon('send', 'w-5 h-5')}
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2.5 w-full">
          <div class="flex items-center gap-2">
            <!-- Live Camera Toggle -->
            <ga-button
              variant="pill"
              icon="video-cam"
              toggle
              ?active="${this.cameraActive}"
              label="${this.cameraActive ? 'Stop Cam' : 'Camera'}"
              @click="${() => this.emit('toggle-camera')}"
            ></ga-button>

            <!-- Screen Share Toggle -->
            <ga-button
              variant="pill"
              icon="screen"
              toggle
              ?active="${this.screenShareActive}"
              label="${this.screenShareActive ? 'Stop Screen' : 'Screen'}"
              @click="${() => this.emit('toggle-screen')}"
            ></ga-button>
          </div>

          <div class="flex items-center gap-2.5 ml-auto">
            <!-- End Session Button -->
            <ga-button
              variant="danger-tonal"
              icon="exit"
              label="End Session"
              loading-label="Leaving..."
              ?loading="${this.terminating}"
              ?disabled="${this.terminating}"
              @click="${() => this.emit('end-session')}"
            ></ga-button>

            <!-- Mic Toggle -->
            <ga-button
              variant="pill"
              active-tone="danger"
              icon="mic"
              toggle
              ?active="${this.recording}"
              ?ping-dot="${this.recording}"
              label="${this.recording ? 'Stop Listening' : 'Click to Speak'}"
              @click="${() => this.emit('toggle-mic')}"
            ></ga-button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'session-control-bar': SessionControlBar;
  }
}
