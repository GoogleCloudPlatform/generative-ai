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
/** User intents emitted by shared session components as `session-action`. */
import { html, nothing } from 'lit';

/**
 * Picture-in-picture preview of the user's camera or shared screen, rendered
 * inside a stage (`position: relative`). It is a template helper rather than
 * an element so the stage can query `#camera-preview` synchronously after
 * its own update. The camera preview is mirrored; screen share is not.
 */
export function renderPipPreview(
  cameraActive: boolean,
  screenShareActive: boolean,
) {
  if (!cameraActive && !screenShareActive) return nothing;
  return html`
    <video
      id="camera-preview"
      autoplay
      playsinline
      muted
      aria-label="${cameraActive ? 'Your camera preview' : 'Your screen share preview'}"
      class="absolute bottom-4 right-4 w-36 h-28 sm:w-44 sm:h-32 rounded-xl object-cover border-2 border-primary shadow-2xl z-20 bg-media-backdrop ${
        cameraActive ? '-scale-x-100' : ''
      }"
    ></video>
  `;
}
