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

import type { AvatarConfigEvent, LiveConfigEvent } from '../domain/presets';
import type { AppSettings } from '../store';
import type { GaTone } from './tokens';

/**
 * Shared detail payload for `ga-change` events emitted by standardized UI
 * primitives (`ga-segmented-control`, `ga-select`, `ga-field`, etc.).
 */
export interface GaChangeDetail<T = string> {
  value: T;
  /** Set by checkbox-like primitives (`ga-checkbox`). */
  checked?: boolean;
}

export type GaChangeEvent<T = string> = CustomEvent<GaChangeDetail<T>>;

export interface GaToastDetail {
  message: string;
  tone?: GaTone;
  durationMs?: number;
}

export type GaToastEvent = CustomEvent<GaToastDetail>;

/**
 * Dispatches a non-blocking, accessible status toast (`role="status"`) handled
 * by `<ga-toast-region>` at the app shell root.
 */
export function showToast(
  message: string,
  tone: GaTone = 'primary',
  durationMs = 3200,
): void {
  globalThis.window?.dispatchEvent(
    new CustomEvent<GaToastDetail>('ga-toast', {
      detail: { message, tone, durationMs },
      bubbles: true,
      composed: true,
    }),
  );
}

declare global {
  interface HTMLElementEventMap {
    'ga-change': GaChangeEvent;
    'ga-toast': GaToastEvent;
    /** From `<avatar-setup>` / `<live-setup>` when the user starts a session. */
    connect: CustomEvent<AvatarConfigEvent | LiveConfigEvent>;
    /** From session views (via LiveSocketController) when a session ends. */
    disconnect: CustomEvent<void>;
  }

  interface WindowEventMap {
    'settings-updated': CustomEvent<AppSettings>;
    'ga-toast': GaToastEvent;
  }
}
