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
import { customElement, property, query, state } from 'lit/decorators.js';
import type { AvatarConfigEvent } from './domain/presets';
import type { GaChangeDetail } from './theme/events';
import type { GaSegmentOption } from './components/ui/ga-segmented-control';
import type { AvatarVideoStage } from './components/avatar/avatar-video-stage';
import { Fmp4PlayerController } from './controllers/fmp4-player-controller';
import { LiveSocketController } from './controllers/live-socket-controller';
import { PcmMicController } from './controllers/pcm-mic-controller';
import { VisionCaptureController } from './controllers/vision-capture-controller';
import './components/ui';
import './components/session';
import type {
  SessionActionDetail,
  SessionSendTextDetail,
} from './components/session/session-events';
import './components/avatar';

const MOBILE_SESSION_TABS: readonly GaSegmentOption<'avatar' | 'transcript'>[] =
  [
    { value: 'avatar', label: 'Avatar View' },
    { value: 'transcript', label: 'Transcript' },
  ];

/**
 * View orchestrator (`<avatar-session>`) coordinating the Live WebSocket
 * switchboard (`LiveSocketController`), media ReactiveControllers
 * (`Fmp4PlayerController`, `PcmMicController`, `VisionCaptureController`), and
 * Tier 2 session domain components (`<avatar-video-stage>`,
 * `<session-control-bar>`, `<session-transcript-panel>`).
 *
 * @fires disconnect - When the session has ended (dispatched by LiveSocketController).
 */
@customElement('avatar-session')
export class AvatarSession extends LitElement {
  @property({ type: Object })
  config!: AvatarConfigEvent;

  @state() private mobileTab: 'avatar' | 'transcript' = 'avatar';

  @query('avatar-video-stage') private stageEl?: AvatarVideoStage;

  private readonly liveSocket = new LiveSocketController(this);
  private readonly fmp4Player = new Fmp4PlayerController(this);
  private readonly pcmMic = new PcmMicController(this);
  private readonly visionCapture = new VisionCaptureController(this);

  protected override createRenderRoot() {
    return this;
  }

  override async firstUpdated(): Promise<void> {
    this.liveSocket.connect({
      endpoint: '/ws',
      config: this.config,
      onBinaryFrame: (data) => {
        this.fmp4Player.appendChunk(new Uint8Array(data));
      },
      onMediaConfig: (msg) => {
        if (typeof msg.codecs === 'string' && msg.codecs) {
          this.fmp4Player.setCodec(msg.codecs);
        }
      },
      onInterrupted: () => {
        this.fmp4Player.flushAndAbort();
      },
      onBeforeTerminate: () => {
        this.visionCapture.stopAll();
        this.pcmMic.stop();
      },
    });

    await this.stageEl?.updateComplete;
    const videoEl =
      this.stageEl?.videoEl ??
      this.querySelector<HTMLVideoElement>('#video-player');
    if (videoEl) {
      this.fmp4Player.attach(videoEl);
    }
  }

  private getPreviewVideoEl = async (): Promise<HTMLVideoElement | null> => {
    await this.stageEl?.updateComplete;
    return (
      this.stageEl?.cameraVideoEl ??
      this.querySelector<HTMLVideoElement>('#camera-preview')
    );
  };

  private async handleToggleMic() {
    await this.pcmMic.toggle((base64Data) => {
      this.liveSocket.sendAudioChunk(base64Data);
    });
  }

  private async handleToggleCamera() {
    await this.visionCapture.toggleCamera(
      this.getPreviewVideoEl,
      (base64Jpeg) => {
        this.liveSocket.sendVideoFrame(base64Jpeg);
      },
    );
  }

  private async handleToggleScreen() {
    await this.visionCapture.toggleScreenShare(
      this.getPreviewVideoEl,
      (base64Jpeg) => {
        this.liveSocket.sendVideoFrame(base64Jpeg);
      },
    );
  }

  private handleSendText(e: CustomEvent<SessionSendTextDetail>) {
    this.liveSocket.sendText(e.detail.text);
  }

  private endSession() {
    this.liveSocket.terminate();
  }

  private handleSessionAction(e: CustomEvent<SessionActionDetail>) {
    switch (e.detail.action) {
      case 'toggle-mic':
        void this.handleToggleMic();
        break;
      case 'toggle-camera':
        void this.handleToggleCamera();
        break;
      case 'toggle-screen':
        void this.handleToggleScreen();
        break;
      case 'end-session':
        this.endSession();
        break;
    }
  }

  protected override render() {
    return html`
      <div class="flex flex-col lg:flex-row h-full gap-4 lg:gap-6 min-h-0">
        <!-- Mobile Tabs (Visible only on small screens) -->
        <div class="lg:hidden shrink-0">
          <ga-segmented-control
            aria-label="Session view"
            .options="${MOBILE_SESSION_TABS}"
            .value="${this.mobileTab}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
              (this.mobileTab = e.detail.value as 'avatar' | 'transcript')}"
          ></ga-segmented-control>
        </div>

        <!-- Left Side: Video Stage & Controls -->
        <div
          class="flex-1 flex-col h-full bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden min-h-0 ${
            this.mobileTab === 'avatar' ? 'flex' : 'hidden lg:flex'
          }"
        >
          <avatar-video-stage
            class="flex-1 flex flex-col min-h-0"
            .status="${this.liveSocket.status}"
            .voiceName="${this.config.voiceName}"
            .sessionModel="${this.liveSocket.sessionModel}"
            .sessionLocation="${this.liveSocket.sessionLocation}"
            ?has-received-video="${this.fmp4Player.hasReceivedVideo}"
            ?terminating="${this.liveSocket.isTerminating}"
            ?recording="${this.pcmMic.isRecording}"
            ?camera-active="${this.visionCapture.isCameraActive}"
            ?screen-share-active="${this.visionCapture.isScreenShareActive}"
          ></avatar-video-stage>

          <session-control-bar
            ?camera-active="${this.visionCapture.isCameraActive}"
            ?screen-share-active="${this.visionCapture.isScreenShareActive}"
            ?recording="${this.pcmMic.isRecording}"
            ?terminating="${this.liveSocket.isTerminating}"
            @session-send-text="${this.handleSendText}"
            @session-action="${this.handleSessionAction}"
          ></session-control-bar>
        </div>

        <!-- Right Side: Sidebar Transcript -->
        <div
          class="w-full lg:w-96 bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-sm flex-col flex-1 lg:flex-none lg:h-auto overflow-hidden min-h-0 ${
            this.mobileTab === 'transcript' ? 'flex' : 'hidden lg:flex'
          }"
        >
          <session-transcript-panel
            class="flex-1 flex flex-col min-h-0 h-full"
            assistant-label="avatar"
            .entries="${this.liveSocket.transcript}"
          ></session-transcript-panel>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-session': AvatarSession;
  }
}
