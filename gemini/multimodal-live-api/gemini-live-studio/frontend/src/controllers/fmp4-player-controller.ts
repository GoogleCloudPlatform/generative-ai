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

/**
 * ReactiveController managing MSE (`MediaSource` / `SourceBuffer`) fMP4 video
 * playback, dynamic codec negotiation, interruption flushing, quota eviction,
 * and inter-turn PTS gap jumping so the avatar never stalls between speech turns.
 */
export class Fmp4PlayerController implements ReactiveController {
  hasReceivedVideo = false;
  configuredCodec = 'avc1.42C020, mp4a.40.2';

  private readonly host: ReactiveControllerHost;
  private videoEl: HTMLVideoElement | null = null;
  private mediaSource: MediaSource | null = null;
  private sourceBuffer: SourceBuffer | null = null;
  private bufferQueue: Uint8Array[] = [];
  private objectUrl: string | null = null;
  private pendingTrimFuture = false;

  private readonly handleSourceOpen = (): void => {
    this.initSourceBuffer();
  };

  private readonly handleSourceError = (e: Event): void => {
    console.error('MediaSource error:', e);
  };

  private readonly handleSourceBufferUpdateEnd = (): void => {
    this.onSourceBufferUpdateEnd();
  };

  private readonly handleSourceBufferError = (e: Event): void => {
    console.error('SourceBuffer error:', e);
  };

  private readonly handleVideoError = (): void => {
    if (this.videoEl?.error) {
      console.error('HTMLVideoElement error:', this.videoEl.error);
    }
  };

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}

  hostDisconnected(): void {
    this.destroy();
  }

  attach(videoEl: HTMLVideoElement): void {
    this.destroy();
    this.videoEl = videoEl;
    this.videoEl.addEventListener('error', this.handleVideoError);
    this.mediaSource = new MediaSource();
    this.mediaSource.addEventListener('sourceopen', this.handleSourceOpen);
    this.mediaSource.addEventListener('error', this.handleSourceError);
    this.objectUrl = URL.createObjectURL(this.mediaSource);
    this.videoEl.src = this.objectUrl;
  }

  setCodec(codecs: string): void {
    if (!codecs || codecs === this.configuredCodec) return;
    this.configuredCodec = codecs;

    if (
      this.sourceBuffer &&
      typeof this.sourceBuffer.changeType === 'function'
    ) {
      const mimeCodec = `video/mp4; codecs="${codecs}"`;
      if (MediaSource.isTypeSupported(mimeCodec)) {
        try {
          this.sourceBuffer.changeType(mimeCodec);
        } catch (e) {
          console.warn('SourceBuffer.changeType failed:', e);
        }
      }
    }
  }

  appendChunk(chunk: Uint8Array): void {
    this.bufferQueue.push(chunk);
    if (!this.hasReceivedVideo) {
      this.hasReceivedVideo = true;
      this.host.requestUpdate();
    }
    this.processBufferQueue();
  }

  flushAndAbort(): void {
    this.bufferQueue = [];
    this.pendingTrimFuture = false;
    if (!this.sourceBuffer) return;

    if (this.sourceBuffer.updating) {
      try {
        this.sourceBuffer.abort();
      } catch (e) {
        console.error('Failed to abort SourceBuffer', e);
      }
    }

    if (this.sourceBuffer.updating) {
      this.pendingTrimFuture = true;
    } else {
      this.trimFutureBufferedMedia();
    }
  }

  destroy(): void {
    this.bufferQueue = [];
    this.pendingTrimFuture = false;
    if (this.sourceBuffer) {
      this.sourceBuffer.removeEventListener(
        'updateend',
        this.handleSourceBufferUpdateEnd,
      );
      this.sourceBuffer.removeEventListener(
        'error',
        this.handleSourceBufferError,
      );
      this.sourceBuffer = null;
    }
    if (this.mediaSource) {
      this.mediaSource.removeEventListener('sourceopen', this.handleSourceOpen);
      this.mediaSource.removeEventListener('error', this.handleSourceError);
      this.mediaSource = null;
    }
    if (this.videoEl) {
      this.videoEl.removeEventListener('error', this.handleVideoError);
      this.videoEl.removeAttribute('src');
      this.videoEl.load();
      this.videoEl = null;
    }
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = null;
    }
  }

  private trimFutureBufferedMedia(): void {
    if (
      !this.sourceBuffer ||
      this.sourceBuffer.updating ||
      !this.mediaSource ||
      this.mediaSource.readyState !== 'open'
    ) {
      return;
    }
    try {
      const buffered = this.sourceBuffer.buffered;
      if (buffered.length === 0) return;
      const cur = this.videoEl ? this.videoEl.currentTime : 0;
      const bufferedEnd = buffered.end(buffered.length - 1);
      if (bufferedEnd > cur + 0.05) {
        this.sourceBuffer.remove(Math.max(0, cur), Infinity);
      }
    } catch (e) {
      console.warn('Failed to trim future SourceBuffer range:', e);
    }
  }

  private evictOldBufferedMedia(): boolean {
    if (
      !this.sourceBuffer ||
      this.sourceBuffer.updating ||
      !this.mediaSource ||
      this.mediaSource.readyState !== 'open'
    ) {
      return false;
    }
    try {
      const buffered = this.sourceBuffer.buffered;
      if (buffered.length === 0) return false;
      const start = buffered.start(0);
      const cur = this.videoEl ? this.videoEl.currentTime : 0;
      const removeEnd = Math.max(start + 1, cur - 5);
      if (removeEnd > start && removeEnd <= buffered.end(buffered.length - 1)) {
        this.sourceBuffer.remove(start, removeEnd);
        return true;
      }
    } catch (e) {
      console.warn('Failed to evict old SourceBuffer range:', e);
    }
    return false;
  }

  private initSourceBuffer(): void {
    if (
      !this.mediaSource ||
      this.mediaSource.readyState !== 'open' ||
      this.sourceBuffer
    ) {
      return;
    }

    const mimeCodec = `video/mp4; codecs="${this.configuredCodec}"`;
    const fallbackCodec = 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"';

    let targetCodec = mimeCodec;
    if (!MediaSource.isTypeSupported(targetCodec)) {
      console.warn(
        `MIME type ${targetCodec} not supported, falling back to ${fallbackCodec}`,
      );
      targetCodec = fallbackCodec;
    }

    if (MediaSource.isTypeSupported(targetCodec)) {
      try {
        this.sourceBuffer = this.mediaSource.addSourceBuffer(targetCodec);
      } catch (e) {
        console.error('Failed to create SourceBuffer with target codec', e);
        try {
          this.sourceBuffer = this.mediaSource.addSourceBuffer('video/mp4');
        } catch (e2) {
          console.error('All SourceBuffer attempts failed', e2);
        }
      }
    } else {
      console.error('Browser does not support fMP4 video playback');
    }

    if (this.sourceBuffer) {
      this.sourceBuffer.addEventListener(
        'updateend',
        this.handleSourceBufferUpdateEnd,
      );
      this.sourceBuffer.addEventListener('error', this.handleSourceBufferError);
      // Drain any chunks queued before sourceopen fired.
      this.processBufferQueue();
    }
  }

  private onSourceBufferUpdateEnd(): void {
    if (this.pendingTrimFuture) {
      this.pendingTrimFuture = false;
      this.trimFutureBufferedMedia();
      if (this.sourceBuffer?.updating) return;
    }

    this.processBufferQueue();

    // Inter-Turn Gap Jumping & Demuxer Underflow Mitigation:
    // Gemini Live only sends fMP4 packets during active vocalization turns.
    // Between turns, the browser media demuxer stalls at the end of turn N
    // (BUFFERING_HAVE_NOTHING). When turn N+1 arrives with a later PTS, jump
    // currentTime across the unbuffered gap so the avatar never freezes.
    if (
      this.sourceBuffer &&
      this.videoEl &&
      this.sourceBuffer.buffered.length > 0
    ) {
      const numRanges = this.sourceBuffer.buffered.length;
      const latestStart = this.sourceBuffer.buffered.start(numRanges - 1);

      if (
        this.videoEl.currentTime < latestStart - 0.1 ||
        (numRanges > 1 && this.videoEl.currentTime < latestStart)
      ) {
        this.videoEl.currentTime = latestStart;
      }

      if (this.videoEl.paused && this.bufferQueue.length === 0) {
        this.videoEl
          .play()
          .catch((e) => console.warn('Autoplay wait on updateend:', e));
      }
    }
  }

  private processBufferQueue(): void {
    if (
      this.sourceBuffer &&
      !this.sourceBuffer.updating &&
      this.bufferQueue.length > 0
    ) {
      const chunk = this.bufferQueue.shift()!;
      try {
        this.sourceBuffer.appendBuffer(chunk as unknown as BufferSource);
        if (this.videoEl && this.videoEl.paused) {
          this.videoEl.play().catch((e) => console.warn('Autoplay wait:', e));
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === 'QuotaExceededError') {
          this.bufferQueue.unshift(chunk);
          if (!this.evictOldBufferedMedia()) {
            // If nothing could be evicted, drop the oldest queued chunk to avoid an infinite loop.
            this.bufferQueue.shift();
          }
        } else {
          console.error('Error appending video buffer:', e);
        }
      }
    }
  }
}
