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

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import { showToast } from '../theme/events';

/**
 * ReactiveController managing 1 FPS live camera and 1 FPS screen-share vision
 * streams during a Gemini Live session.
 *
 * Captures at native device frame rate for a smooth PiP preview while sampling
 * JPEG frames at 1 FPS for upstream transmission.
 */
export class VisionCaptureController implements ReactiveController {
  isCameraActive = false;
  isScreenShareActive = false;

  private readonly host: ReactiveControllerHost;
  private cameraMediaStream: MediaStream | null = null;
  private cameraIntervalId: ReturnType<typeof setInterval> | null = null;
  private screenShareMediaStream: MediaStream | null = null;
  private screenShareIntervalId: ReturnType<typeof setInterval> | null = null;
  private cameraToken = 0;
  private screenToken = 0;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.stopAll();
  }

  stopAll(): void {
    this.stopCamera();
    this.stopScreenShare();
  }

  async toggleCamera(
    getPreviewEl: () =>
      | Promise<HTMLVideoElement | null | undefined>
      | HTMLVideoElement
      | null
      | undefined,
    onJpegFrame: (base64Jpeg: string) => void,
  ): Promise<void> {
    if (this.isCameraActive) {
      this.stopCamera();
    } else {
      await this.startCamera(getPreviewEl, onJpegFrame);
    }
  }

  async startCamera(
    getPreviewEl: () =>
      | Promise<HTMLVideoElement | null | undefined>
      | HTMLVideoElement
      | null
      | undefined,
    onJpegFrame: (base64Jpeg: string) => void,
  ): Promise<void> {
    if (this.isScreenShareActive) {
      this.stopScreenShare();
    }
    const token = ++this.cameraToken;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
      });
      if (token !== this.cameraToken) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      if (this.cameraMediaStream) {
        this.cameraMediaStream.getTracks().forEach((t) => t.stop());
      }
      this.cameraMediaStream = stream;
      this.isCameraActive = true;
      this.host.requestUpdate();
      await this.host.updateComplete;
      if (token !== this.cameraToken) {
        this.stopCamera();
        return;
      }

      const previewEl = await getPreviewEl();
      if (token !== this.cameraToken) {
        this.stopCamera();
        return;
      }
      if (previewEl) {
        previewEl.srcObject = this.cameraMediaStream;
        await previewEl.play();
        if (token !== this.cameraToken) {
          this.stopCamera();
          return;
        }
      }

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      this.cameraIntervalId = setInterval(async () => {
        const videoEl = previewEl ?? (await getPreviewEl());
        if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) return;

        canvas.width = videoEl.videoWidth;
        canvas.height = videoEl.videoHeight;
        ctx?.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        const base64Data = dataUrl.split(',')[1];
        if (base64Data) {
          onJpegFrame(base64Data);
        }
      }, 1000);
    } catch (err) {
      console.error('Failed to access camera for live vision:', err);
      this.stopCamera();
      showToast(
        'Camera access denied or unavailable. Check browser permissions.',
        'danger',
      );
    }
  }

  stopCamera(): void {
    this.cameraToken++;
    if (this.cameraIntervalId) {
      clearInterval(this.cameraIntervalId);
      this.cameraIntervalId = null;
    }
    if (this.cameraMediaStream) {
      this.cameraMediaStream.getTracks().forEach((t) => t.stop());
      this.cameraMediaStream = null;
    }
    if (this.isCameraActive) {
      this.isCameraActive = false;
      this.host.requestUpdate();
    }
  }

  async toggleScreenShare(
    getPreviewEl: () =>
      | Promise<HTMLVideoElement | null | undefined>
      | HTMLVideoElement
      | null
      | undefined,
    onJpegFrame: (base64Jpeg: string) => void,
  ): Promise<void> {
    if (this.isScreenShareActive) {
      this.stopScreenShare();
    } else {
      await this.startScreenShare(getPreviewEl, onJpegFrame);
    }
  }

  async startScreenShare(
    getPreviewEl: () =>
      | Promise<HTMLVideoElement | null | undefined>
      | HTMLVideoElement
      | null
      | undefined,
    onJpegFrame: (base64Jpeg: string) => void,
  ): Promise<void> {
    if (this.isCameraActive) {
      this.stopCamera();
    }
    const token = ++this.screenToken;
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (token !== this.screenToken) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      if (this.screenShareMediaStream) {
        this.screenShareMediaStream.getTracks().forEach((t) => t.stop());
      }
      this.screenShareMediaStream = stream;
      this.isScreenShareActive = true;
      this.host.requestUpdate();
      await this.host.updateComplete;
      if (token !== this.screenToken) {
        this.stopScreenShare();
        return;
      }

      const track = this.screenShareMediaStream.getVideoTracks()[0];
      if (track) {
        track.onended = () => {
          this.stopScreenShare();
        };
      }

      const previewEl = await getPreviewEl();
      if (token !== this.screenToken) {
        this.stopScreenShare();
        return;
      }
      if (previewEl) {
        previewEl.srcObject = this.screenShareMediaStream;
        await previewEl.play();
        if (token !== this.screenToken) {
          this.stopScreenShare();
          return;
        }
      }

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      this.screenShareIntervalId = setInterval(async () => {
        const videoEl = previewEl ?? (await getPreviewEl());
        if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) return;

        let w = videoEl.videoWidth;
        let h = videoEl.videoHeight;
        const maxDim = 1280;
        if (w > maxDim || h > maxDim) {
          if (w > h) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          } else {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }

        canvas.width = w;
        canvas.height = h;
        ctx?.drawImage(videoEl, 0, 0, w, h);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
        const base64Data = dataUrl.split(',')[1];
        if (base64Data) {
          onJpegFrame(base64Data);
        }
      }, 1000);
    } catch (err) {
      console.error('Failed to start screen share:', err);
      this.stopScreenShare();
      showToast('Screen share cancelled or unavailable.', 'danger');
    }
  }

  stopScreenShare(): void {
    this.screenToken++;
    if (this.screenShareIntervalId) {
      clearInterval(this.screenShareIntervalId);
      this.screenShareIntervalId = null;
    }
    if (this.screenShareMediaStream) {
      this.screenShareMediaStream.getTracks().forEach((t) => {
        t.onended = null;
        t.stop();
      });
      this.screenShareMediaStream = null;
    }
    if (this.isScreenShareActive) {
      this.isScreenShareActive = false;
      this.host.requestUpdate();
    }
  }
}
