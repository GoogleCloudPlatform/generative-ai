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
import { customElement, property, query } from 'lit/decorators.js';
import { renderIcon } from '../ui/icons';
import '../session/session-stage-header';
import { renderPipPreview } from '../session/session-pip-preview';

/**
 * Domain component (`<avatar-video-stage>`) rendering the session status bar,
 * fMP4 avatar `<video>` stage, PiP live camera/screen preview, initializing
 * overlay, and pulsing microphone aura.
 */
@customElement('avatar-video-stage')
export class AvatarVideoStage extends LitElement {
  @property({ type: String }) status = 'Connecting...';
  @property({ type: String, attribute: 'voice-name' }) voiceName = '';
  @property({ type: String, attribute: 'session-model' }) sessionModel = '';
  @property({ type: String, attribute: 'session-location' }) sessionLocation =
    '';
  @property({ type: Boolean, attribute: 'has-received-video' })
  hasReceivedVideo = false;
  @property({ type: Boolean }) terminating = false;
  @property({ type: Boolean }) recording = false;
  @property({ type: Boolean, attribute: 'camera-active' }) cameraActive = false;
  @property({ type: Boolean, attribute: 'screen-share-active' })
  screenShareActive = false;

  @query('#video-player') videoEl!: HTMLVideoElement;
  @query('#camera-preview') cameraVideoEl?: HTMLVideoElement;

  protected override createRenderRoot() {
    return this;
  }

  protected override render() {
    return html`
      <div class="flex flex-col flex-1 min-h-0">
        <session-stage-header
          .status="${this.status}"
          .voiceName="${this.voiceName}"
          .sessionModel="${this.sessionModel}"
          .sessionLocation="${this.sessionLocation}"
        ></session-stage-header>

        <!-- Video Area -->
        <div
          class="flex-1 bg-surface-container-highest relative flex items-center justify-center overflow-hidden min-h-0"
        >
          <video
            id="video-player"
            autoplay
            playsinline
            class="h-full w-auto max-w-full object-contain pointer-events-none"
          ></video>

          <!-- PiP Live Camera / Screen Share Preview -->
          ${renderPipPreview(this.cameraActive, this.screenShareActive)}

          ${
            !this.terminating &&
            (this.status !== 'Connected' || !this.hasReceivedVideo)
              ? html`
                <div
                  class="absolute inset-0 flex flex-col items-center justify-center bg-surface-container-highest/80 backdrop-blur-sm z-10"
                >
                  ${renderIcon('spinner', 'h-10 w-10 text-primary mb-4')}
                  <p class="text-on-surface font-semibold tracking-wide">
                    ${
                      this.status === 'Connected' && !this.hasReceivedVideo
                        ? 'Waiting for Avatar stream...'
                        : 'Initializing Session...'
                    }
                  </p>
                </div>
              `
              : nothing
          }

          <!-- Live Stream Aura Effect -->
          ${
            this.recording
              ? html`
                <div
                  class="absolute inset-0 pointer-events-none ring-[12px] ring-tertiary-fixed/30 rounded-lg transition-all duration-1000 animate-pulse"
                ></div>
              `
              : nothing
          }
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-video-stage': AvatarVideoStage;
  }
}
