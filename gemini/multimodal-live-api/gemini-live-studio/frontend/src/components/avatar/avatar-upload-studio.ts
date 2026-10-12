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
import type { UploadTransformMode } from '../../domain/presets';
import { showToast } from '../../theme/events';
import { renderIcon } from '../ui/icons';
import '../ui/ga-badge';
import '../ui/ga-button';
import '../ui/ga-radio-group';
import type { GaRadioOption } from '../ui/ga-radio-group';
import type { GaChangeDetail } from '../../theme/events';

const TRANSFORM_MODES: ReadonlyArray<{
  mode: UploadTransformMode;
  title: string;
  badge?: string;
  description: string;
}> = [
  {
    mode: 'avatar',
    title: 'Avatar Transform',
    badge: '3D',
    description: 'Stylized 3D character portrait via Gemini Image',
  },
  {
    mode: 'none',
    title: 'No Changes',
    description: 'Original photo as-is, auto-cropped (instant)',
  },
  {
    mode: 'remove-bg',
    title: 'Remove Background',
    description: 'Keep real photo & replace with studio backdrop',
  },
];

const TRANSFORM_OPTIONS: readonly GaRadioOption<UploadTransformMode>[] =
  TRANSFORM_MODES.map((m) => ({
    value: m.mode,
    label: m.title,
    badge: m.badge,
    description: m.description,
  }));

export interface AvatarUploadCaptureDetail {
  dataUrl: string;
  source: 'camera' | 'file';
}

export interface AvatarTransformModeChangeDetail {
  mode: UploadTransformMode;
}

/**
 * Custom avatar source (`<avatar-upload-studio>`): file upload, webcam
 * snapshot, and the photo processing mode.
 *
 * @fires avatar-upload-capture - When the user uploads or captures a photo.
 *   Detail: `{ dataUrl, source }`.
 * @fires avatar-transform-mode-change - When the user picks a processing mode.
 *   Detail: `{ mode }`.
 */
@customElement('avatar-upload-studio')
export class AvatarUploadStudio extends LitElement {
  @property({ type: String, attribute: 'transform-mode' })
  transformMode: UploadTransformMode = 'avatar';
  @property({ type: Boolean, attribute: 'processing' }) isProcessing = false;
  @property({ type: Boolean, attribute: 'has-raw-upload' }) hasRawUpload =
    false;

  @state() private isCameraActive = false;
  @state() private videoDevices: MediaDeviceInfo[] = [];
  @state() private selectedDeviceId = '';

  @query('#camera-preview') private cameraVideoEl?: HTMLVideoElement;
  private cameraStream: MediaStream | null = null;
  private cameraToken = 0;

  override disconnectedCallback(): void {
    this.stopCamera();
    super.disconnectedCallback();
  }

  protected override createRenderRoot() {
    return this;
  }

  stopCamera(): void {
    this.cameraToken++;
    this.isCameraActive = false;
    if (this.cameraVideoEl) {
      this.cameraVideoEl.srcObject = null;
    }
    if (this.cameraStream) {
      this.cameraStream.getTracks().forEach((t) => t.stop());
      this.cameraStream = null;
    }
  }

  private async startCamera() {
    this.isCameraActive = true;
    await this.updateComplete;
    const started = await this.updateCameraStream();
    if (started) {
      await this.fetchDevices();
    }
  }

  private async fetchDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      this.videoDevices = devices.filter((d) => d.kind === 'videoinput');
      if (this.videoDevices.length > 0 && !this.selectedDeviceId) {
        this.selectedDeviceId = this.videoDevices[0].deviceId;
      }
    } catch (e) {
      console.error('Failed to list devices', e);
    }
  }

  private async handleCameraChange(e: Event) {
    this.selectedDeviceId = (e.target as HTMLSelectElement).value;
    await this.updateCameraStream();
  }

  private async updateCameraStream(): Promise<boolean> {
    const token = ++this.cameraToken;
    if (this.cameraStream) {
      this.cameraStream.getTracks().forEach((t) => t.stop());
      this.cameraStream = null;
    }
    try {
      const constraints: MediaStreamConstraints = {
        video: this.selectedDeviceId
          ? { deviceId: { exact: this.selectedDeviceId } }
          : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (
        token !== this.cameraToken ||
        !this.isCameraActive ||
        !this.isConnected
      ) {
        stream.getTracks().forEach((t) => t.stop());
        return false;
      }
      this.cameraStream = stream;
      await this.updateComplete;
      if (
        token !== this.cameraToken ||
        !this.isCameraActive ||
        !this.isConnected
      ) {
        this.stopCamera();
        return false;
      }
      if (this.cameraVideoEl) {
        this.cameraVideoEl.srcObject = this.cameraStream;
        await this.cameraVideoEl.play();
      }
      return true;
    } catch (err) {
      console.error('Failed to access camera', err);
      this.stopCamera();
      showToast('Could not access camera.', 'danger');
      return false;
    }
  }

  private captureImage() {
    if (!this.cameraVideoEl) return;
    const canvas = document.createElement('canvas');
    canvas.width = this.cameraVideoEl.videoWidth;
    canvas.height = this.cameraVideoEl.videoHeight;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(this.cameraVideoEl, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
      this.stopCamera();
      this.dispatchEvent(
        new CustomEvent<AvatarUploadCaptureDetail>('avatar-upload-capture', {
          detail: { dataUrl, source: 'camera' },
          bubbles: true,
          composed: true,
        }),
      );
    }
  }

  private handleFileUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      input.value = '';
      this.dispatchEvent(
        new CustomEvent<AvatarUploadCaptureDetail>('avatar-upload-capture', {
          detail: { dataUrl, source: 'file' },
          bubbles: true,
          composed: true,
        }),
      );
    };
    reader.readAsDataURL(file);
  }

  private handleModeChange(e: CustomEvent<GaChangeDetail>) {
    // Translate the primitive's ga-change into this component's domain event.
    e.stopPropagation();
    const mode = e.detail.value as UploadTransformMode;
    this.dispatchEvent(
      new CustomEvent<AvatarTransformModeChangeDetail>(
        'avatar-transform-mode-change',
        {
          detail: { mode },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  protected override render() {
    const modeLabel =
      this.transformMode === 'avatar'
        ? '3D Avatar Transform via Gemini Image'
        : this.transformMode === 'remove-bg'
          ? 'Studio Background Removal via Gemini Image'
          : 'Original Photo (Auto-crop)';

    return html`
      <div>
        <div class="flex items-center justify-between mb-3">
          <h3 class="block text-sm font-semibold text-on-surface">
            Upload Custom Image
          </h3>
          <ga-button
            variant="link"
            label="${this.isCameraActive ? 'Cancel Camera' : 'Use Camera'}"
            @click="${this.isCameraActive ? this.stopCamera : this.startCamera}"
          ></ga-button>
        </div>

        ${
          this.isCameraActive
            ? html`
              <div
                class="border-2 border-outline-variant/50 rounded-2xl overflow-hidden bg-media-backdrop flex flex-col relative h-56"
              >
                ${
                  this.videoDevices.length > 1
                    ? html`
                      <select
                        aria-label="Camera"
                        @change="${this.handleCameraChange}"
                        .value="${this.selectedDeviceId}"
                        class="absolute top-2 left-2 right-2 bg-surface-container-lowest/85 text-on-surface text-xs rounded-lg px-2 py-1 z-10 backdrop-blur-sm border-none"
                      >
                        ${this.videoDevices.map(
                          (d) => html`
                            <option value="${d.deviceId}">
                              ${d.label || 'Camera'}
                            </option>
                          `,
                        )}
                      </select>
                    `
                    : nothing
                }
                <video
                  id="camera-preview"
                  autoplay
                  playsinline
                  class="w-full h-full object-cover"
                ></video>
                <button
                  type="button"
                  aria-label="Capture photo"
                  @click="${this.captureImage}"
                  class="absolute bottom-4 left-1/2 -translate-x-1/2 bg-primary text-on-primary p-3 rounded-full shadow-lg hover:bg-primary-hover z-10 flex items-center justify-center"
                >
                  ${renderIcon('camera', 'w-6 h-6')}
                </button>
              </div>
            `
            : html`
              <div
                class="border-2 border-dashed border-outline-variant/50 rounded-2xl p-6 text-center hover:bg-surface-container-low transition-colors relative cursor-pointer h-44 flex flex-col items-center justify-center"
              >
                <input
                  type="file"
                  accept="image/jpeg, image/png"
                  aria-label="Upload a JPEG or PNG image"
                  @change="${this.handleFileUpload}"
                  class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div
                  class="flex flex-col items-center gap-2 text-on-surface-variant pointer-events-none"
                >
                  <div
                    class="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center"
                  >
                    ${renderIcon('upload', 'w-5 h-5')}
                  </div>
                  <div>
                    <p class="font-semibold text-on-surface text-sm">
                      Click to upload a file
                    </p>
                    <p class="text-xs mt-0.5">JPEG or PNG &bull; ${modeLabel}</p>
                  </div>
                </div>
              </div>
            `
        }

        <!-- 3-Way Photo Processing Mode Selector -->
        <div class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <span
              aria-hidden="true"
              class="text-xs font-bold uppercase tracking-wider text-on-surface-variant"
            >
              Photo Processing Mode
            </span>
            ${
              this.hasRawUpload
                ? html`<ga-badge
                  label="Click to switch live"
                  tone="primary"
                  pill
                ></ga-badge>`
                : nothing
            }
          </div>
          <ga-radio-group
            label="Photo Processing Mode"
            hide-label
            appearance="card"
            .options="${TRANSFORM_OPTIONS}"
            .value="${this.transformMode}"
            ?disabled="${this.isProcessing}"
            @ga-change="${this.handleModeChange}"
          ></ga-radio-group>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-upload-studio': AvatarUploadStudio;
  }
  interface HTMLElementEventMap {
    'avatar-upload-capture': CustomEvent<AvatarUploadCaptureDetail>;
    'avatar-transform-mode-change': CustomEvent<AvatarTransformModeChangeDetail>;
  }
}
