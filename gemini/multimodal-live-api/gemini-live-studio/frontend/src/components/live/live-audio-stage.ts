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
import { customElement, property, query, state } from 'lit/decorators.js';
import { colorTokenReader } from '../../theme/tokens';
import '../ui/ga-badge';
import '../session/session-stage-header';
import { renderPipPreview } from '../session/session-pip-preview';

/**
 * Domain component (`<live-audio-stage>`) rendering the session status bar,
 * 60fps canvas radial audio-reactive visualizer (driven by `AnalyserNode`),
 * speaker mute control, and PiP live camera/screen-share preview.
 */
@customElement('live-audio-stage')
export class LiveAudioStage extends LitElement {
  @property({ type: String }) status = 'Connecting...';
  @property({ type: String, attribute: 'voice-name' }) voiceName = '';
  @property({ type: String, attribute: 'session-model' }) sessionModel = '';
  @property({ type: String, attribute: 'session-location' }) sessionLocation =
    '';
  @property({ type: Boolean }) terminating = false;
  @property({ type: Boolean }) recording = false;
  @property({ type: Boolean }) muted = false;
  @property({ type: Boolean, attribute: 'camera-active' }) cameraActive = false;
  @property({ type: Boolean, attribute: 'screen-share-active' })
  screenShareActive = false;
  @property({ attribute: false }) analyser: AnalyserNode | null = null;

  @state() private isModelSpeaking = false;

  @query('#visualizer-canvas') private canvasEl?: HTMLCanvasElement;
  @query('#camera-preview') cameraVideoEl?: HTMLVideoElement;

  private rafId: number | null = null;
  private reducedMotionTimerId: ReturnType<typeof setInterval> | null = null;
  private freqData = new Uint8Array(128);
  private phase = 0;

  protected override createRenderRoot() {
    return this;
  }

  override firstUpdated(): void {
    this.startVisualizerLoop();
  }

  override disconnectedCallback(): void {
    this.stopVisualizerLoop();
    super.disconnectedCallback();
  }

  private startVisualizerLoop(): void {
    this.stopVisualizerLoop();
    const reducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;

    if (reducedMotion) {
      this.drawVisualizer(true);
      this.reducedMotionTimerId = setInterval(() => {
        this.drawVisualizer(true);
      }, 250);
      return;
    }

    const renderFrame = () => {
      this.drawVisualizer(false);
      this.rafId = requestAnimationFrame(renderFrame);
    };
    this.rafId = requestAnimationFrame(renderFrame);
  }

  private stopVisualizerLoop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.reducedMotionTimerId !== null) {
      clearInterval(this.reducedMotionTimerId);
      this.reducedMotionTimerId = null;
    }
  }

  private drawVisualizer(reducedMotion: boolean): void {
    const canvas = this.canvasEl;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const c = colorTokenReader(this);

    const dpr = window.devicePixelRatio || 1;
    const width = 320;
    const height = 320;
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    let avgEnergy = 0;
    if (this.analyser) {
      if (this.freqData.length !== this.analyser.frequencyBinCount) {
        this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
      }
      this.analyser.getByteFrequencyData(this.freqData);
      let sum = 0;
      const bins = Math.min(48, this.freqData.length);
      for (let i = 0; i < bins; i++) {
        sum += this.freqData[i];
      }
      avgEnergy = bins > 0 ? sum / bins / 255 : 0;
    }

    const speakingNow = avgEnergy > 0.03;
    if (speakingNow !== this.isModelSpeaking) {
      this.isModelSpeaking = speakingNow;
    }

    if (!reducedMotion) {
      this.phase += 0.035;
    }

    const cx = width / 2;
    const cy = height / 2;
    const baseRadius = 58;
    const dynamicBoost = avgEnergy * 34;
    const idlePulse = reducedMotion ? 0 : Math.sin(this.phase) * 3;
    const orbRadius = baseRadius + dynamicBoost + idlePulse;

    // Outer ambient glow
    const glowRadius = orbRadius * 1.9;
    const glowGrad = ctx.createRadialGradient(
      cx,
      cy,
      orbRadius * 0.4,
      cx,
      cy,
      glowRadius,
    );
    if (speakingNow) {
      glowGrad.addColorStop(0, c('viz-speaking', 0.38));
      glowGrad.addColorStop(0.55, c('viz-speaking-highlight', 0.16));
      glowGrad.addColorStop(1, c('viz-speaking', 0));
    } else if (this.recording) {
      glowGrad.addColorStop(0, c('viz-listening', 0.28));
      glowGrad.addColorStop(0.55, c('viz-listening-accent', 0.12));
      glowGrad.addColorStop(1, c('viz-listening', 0));
    } else {
      glowGrad.addColorStop(0, c('viz-speaking', 0.18));
      glowGrad.addColorStop(1, c('viz-speaking', 0));
    }
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, glowRadius, 0, Math.PI * 2);
    ctx.fill();

    // Radial frequency bars (48 spokes around the orb)
    const numBars = 48;
    const barStartRadius = orbRadius + 8;
    for (let i = 0; i < numBars; i++) {
      const angle = (i / numBars) * Math.PI * 2 - Math.PI / 2;
      const binIdx = Math.floor((i / numBars) * 36);
      const rawVal = this.analyser ? (this.freqData[binIdx] || 0) / 255 : 0;
      const micWave =
        this.recording && !speakingNow && !reducedMotion
          ? (Math.sin(this.phase * 2.5 + i * 0.45) * 0.5 + 0.5) * 0.28
          : 0;
      const mag = Math.max(rawVal, micWave);
      const barLength = 6 + mag * 46;

      const x1 = cx + Math.cos(angle) * barStartRadius;
      const y1 = cy + Math.sin(angle) * barStartRadius;
      const x2 = cx + Math.cos(angle) * (barStartRadius + barLength);
      const y2 = cy + Math.sin(angle) * (barStartRadius + barLength);

      ctx.strokeStyle = speakingNow
        ? c('viz-speaking', 0.35 + mag * 0.65)
        : this.recording
          ? c('viz-listening', 0.3 + mag * 0.6)
          : c('viz-bar-idle', 0.25);
      ctx.lineWidth = 3.5;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Core orb gradient
    const coreGrad = ctx.createRadialGradient(
      cx - orbRadius * 0.28,
      cy - orbRadius * 0.28,
      orbRadius * 0.1,
      cx,
      cy,
      orbRadius,
    );
    if (speakingNow) {
      coreGrad.addColorStop(0, c('viz-speaking-highlight'));
      coreGrad.addColorStop(0.65, c('viz-speaking'));
      coreGrad.addColorStop(1, c('viz-speaking-deep'));
    } else if (this.recording) {
      coreGrad.addColorStop(0, c('viz-listening-highlight'));
      coreGrad.addColorStop(0.65, c('viz-listening'));
      coreGrad.addColorStop(1, c('viz-listening-deep'));
    } else {
      coreGrad.addColorStop(0, c('viz-idle-highlight'));
      coreGrad.addColorStop(0.75, c('viz-speaking'));
      coreGrad.addColorStop(1, c('viz-idle-deep'));
    }

    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  protected override render() {
    const activityCaption = this.terminating
      ? 'Wrapping up live session...'
      : this.status !== 'Connected'
        ? 'Connecting to Gemini Live...'
        : this.isModelSpeaking
          ? `Gemini (${this.voiceName}) is speaking...`
          : this.recording
            ? 'Listening — speak naturally or interrupt anytime'
            : 'Connected — Click to Speak or type a message below';

    return html`
      <div class="flex flex-col flex-1 min-h-0">
        <session-stage-header
          mute-toggle
          .status="${this.status}"
          .voiceName="${this.voiceName}"
          .sessionModel="${this.sessionModel}"
          .sessionLocation="${this.sessionLocation}"
          .muted="${this.muted}"
        ></session-stage-header>

        <!-- Audio-Reactive Stage Area -->
        <div
          class="flex-1 bg-surface-container-low relative flex flex-col items-center justify-center overflow-hidden min-h-[280px] p-6"
        >
          <canvas
            id="visualizer-canvas"
            role="img"
            class="w-72 h-72 sm:w-80 sm:h-80 pointer-events-none"
            aria-label="Gemini Live Audio Reactive Visualizer"
          ></canvas>

          <div class="mt-2 flex flex-col items-center gap-1.5 z-10 text-center">
            <p class="text-sm font-semibold text-on-surface">
              ${activityCaption}
            </p>
            ${
              this.muted
                ? html`<ga-badge
                  label="Speaker Muted • Visualizer Active"
                  tone="danger"
                  pill
                ></ga-badge>`
                : nothing
            }
          </div>

          <!-- PiP Live Camera / Screen Share Preview -->
          ${renderPipPreview(this.cameraActive, this.screenShareActive)}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'live-audio-stage': LiveAudioStage;
  }
}
