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

import { html, type ReactiveControllerHost } from 'lit';

const PRESET_IMAGE_BASE =
  'https://www.gstatic.com/pantheon/images/aiplatform/vertex_ai_studio/avatars';

// Presets whose CDN thumbnail is not <name>.png (carmen.png was removed and
// replaced by carmen_2.png).
const PRESET_IMAGE_FILES: Partial<Record<string, string>> = {
  carmen: 'carmen_2.png',
};

// Preset thumbnails are hosted on Google's CDN, not in this repo, and an
// individual image can disappear while the preset itself still works in the
// Live API; renderPresetThumb() then falls back to the preset's initial.
export function presetImageUrl(name: string): string {
  const key = name.toLowerCase();
  return `${PRESET_IMAGE_BASE}/${PRESET_IMAGE_FILES[key] ?? `${key}.png`}`;
}

// Image URLs that failed to load this page session, so
// re-renders show the initial immediately instead of re-requesting a 404.
const failedImages = new Set<string>();

/** Upper-case first letter of a preset name, shown when its image is missing. */
export function presetInitial(name: string): string {
  return (name.trim().charAt(0) || '?').toUpperCase();
}

/**
 * Renders a preset thumbnail, or a theme-aware initial (token classes, so it
 * follows light/dark) when the CDN image is missing. `host` re-renders once
 * the image fails.
 */
export function renderPresetThumb(
  name: string,
  host: ReactiveControllerHost,
  imgClass: string,
  initialClass: string,
) {
  const src = presetImageUrl(name);
  if (failedImages.has(src)) {
    return html`<span
      role="img"
      aria-label="${name}"
      class="${initialClass} bg-surface-container-highest text-on-surface-variant font-semibold flex items-center justify-center select-none"
      >${presetInitial(name)}</span
    >`;
  }
  return html`<img
    src="${src}"
    alt="${name}"
    class="${imgClass}"
    @error="${() => {
      failedImages.add(src);
      host.requestUpdate();
    }}"
  />`;
}
