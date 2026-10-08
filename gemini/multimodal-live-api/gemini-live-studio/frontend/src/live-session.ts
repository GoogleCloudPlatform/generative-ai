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
import type { LiveConfigEvent } from './domain/presets';
import type { GaChangeDetail } from './theme/events';
import type { GaSegmentOption } from './components/ui/ga-segmented-control';
import type { LiveAudioStage } from './components/live/live-audio-stage';
import { LiveSocketController } from './controllers/live-socket-controller';
import { PcmPlayerController } from './controllers/pcm-player-controller';
import { PcmMicController } from './controllers/pcm-mic-controller';
import { VisionCaptureController } from './controllers/vision-capture-controller';
import './components/ui';
import './components/session';
import type {
  SessionActionDetail,
  SessionSendTextDetail,
} from './components/session/session-events';
import './components/live/live-audio-stage';

const MOBILE_LIVE_TABS: readonly GaSegmentOption<'stage' | 'transcript'>[] = [
  { value: 'stage', label: 'Audio Stage' },
  { value: 'transcript', label: 'Transcript' },
];

/**
 * View orchestrator (`<live-session>`) coordinating the `/ws/live` WebSocket
 * switchboard (`LiveSocketController`), `PcmPlayerController` (24kHz gapless
 * Web Audio + `AnalyserNode`), `PcmMicController`, `VisionCaptureController`,
 * `<live-audio-stage>`, `<session-control-bar>`, and `<session-transcript-panel>`.
 *
 * @fires disconnect - When the session has ended (dispatched by LiveSocketController).
 */
@customElement('live-session')
export class LiveSession extends LitElement {
  @property({ type: Object })
  config!: LiveConfigEvent;

  @state() private mobileTab: 'stage' | 'transcript' = 'stage';

  @query('live-audio-stage') private stageEl?: LiveAudioStage;

  private readonly liveSocket = new LiveSocketController(this);
  private readonly pcmPlayer = new PcmPlayerController(this);
  private readonly pcmMic = new PcmMicController(this);
  private readonly visionCapture = new VisionCaptureController(this);

  protected override createRenderRoot() {
    return this;
  }

  override firstUpdated(): void {
    this.pcmPlayer.init(24000);
    this.liveSocket.connect({
      endpoint: '/ws/live',
      config: this.config,
      onBinaryFrame: (data) => {
        this.pcmPlayer.feed(data);
      },
      onMediaConfig: (msg) => {
        if (typeof msg.sampleRate === 'number' && msg.sampleRate > 0) {
          this.pcmPlayer.init(msg.sampleRate);
        }
      },
      onInterrupted: () => {
        this.pcmPlayer.flushAndInterrupt();
      },
      onBeforeTerminate: () => {
        this.visionCapture.stopAll();
        this.pcmMic.stop();
      },
    });
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
      case 'toggle-mute':
        this.pcmPlayer.toggleMute();
        break;
    }
  }

  protected override render() {
    return html`
      <div class="flex flex-col lg:flex-row h-full gap-4 lg:gap-6 min-h-0">
        <!-- Mobile Tabs (Visible only on small screens) -->
        <div class="lg:hidden shrink-0">
          <ga-segmented-control
            aria-label="Live session view"
            .options="${MOBILE_LIVE_TABS}"
            .value="${this.mobileTab}"
            @ga-change="${(e: CustomEvent<GaChangeDetail>) =>
              (this.mobileTab = e.detail.value as 'stage' | 'transcript')}"
          ></ga-segmented-control>
        </div>

        <!-- Left Side: Audio Stage & Controls -->
        <div
          class="flex-1 flex-col h-full bg-surface-container-lowest rounded-2xl border border-outline-variant/20 shadow-sm overflow-hidden min-h-0 ${
            this.mobileTab === 'stage' ? 'flex' : 'hidden lg:flex'
          }"
        >
          <live-audio-stage
            class="flex-1 flex flex-col min-h-0"
            .status="${this.liveSocket.status}"
            .voiceName="${this.config.voiceName}"
            .sessionModel="${this.liveSocket.sessionModel}"
            .sessionLocation="${this.liveSocket.sessionLocation}"
            .analyser="${this.pcmPlayer.analyser}"
            ?terminating="${this.liveSocket.isTerminating}"
            ?recording="${this.pcmMic.isRecording}"
            ?muted="${this.pcmPlayer.isMuted}"
            ?camera-active="${this.visionCapture.isCameraActive}"
            ?screen-share-active="${this.visionCapture.isScreenShareActive}"
            @session-action="${this.handleSessionAction}"
          ></live-audio-stage>

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
            assistant-label="gemini"
            .entries="${this.liveSocket.transcript}"
          ></session-transcript-panel>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'live-session': LiveSession;
  }
}
