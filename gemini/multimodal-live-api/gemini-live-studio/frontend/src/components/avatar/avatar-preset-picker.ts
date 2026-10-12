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
import { customElement, property } from 'lit/decorators.js';
import { PRESETS } from '../../domain/presets';
import { presetImageUrl, presetInitial } from '../../preset-image';
import type { GaChangeDetail } from '../../theme/events';
import '../ui/ga-radio-group';
import type { GaRadioOption } from '../ui/ga-radio-group';

const PRESET_OPTIONS: readonly GaRadioOption[] = PRESETS.map((name) => ({
  value: name,
  label: name,
  imageSrc: presetImageUrl(name),
  imageFallbackText: presetInitial(name),
}));

/**
 * Preset avatar picker (`<avatar-preset-picker>`): a `ga-radio-group` of the
 * built-in Live API avatars with thumbnails.
 *
 * @fires ga-change - Bubbles from the inner `ga-radio-group` when the user
 *   picks a preset. Detail: `{ value }` (the preset name).
 */
@customElement('avatar-preset-picker')
export class AvatarPresetPicker extends LitElement {
  @property({ type: String }) value = 'Ben';

  protected override createRenderRoot() {
    return this;
  }

  protected override render() {
    return html`
      <ga-radio-group
        label="Select Preset Avatar"
        appearance="tile"
        layout-class="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-2"
        .options="${PRESET_OPTIONS}"
        .value="${this.value}"
        @ga-change="${(e: CustomEvent<GaChangeDetail>) => (this.value = e.detail.value)}"
      ></ga-radio-group>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'avatar-preset-picker': AvatarPresetPicker;
  }
}
