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
import { afterEach, describe, expect, it } from 'vitest';
import { html } from 'lit';
import { userEvent } from 'vitest/browser';
import {
  cleanupFixtures,
  expectAccessible,
  fixture,
  recordEvents,
} from '../../test/fixture';
import type { GaChangeDetail } from '../../theme/events';
import './avatar-preset-picker';
import './avatar-prompt-generator';
import './avatar-upload-studio';
import type { AvatarPresetPicker } from './avatar-preset-picker';
import type { AvatarPromptDetail } from './avatar-prompt-generator';
import type { AvatarTransformModeChangeDetail } from './avatar-upload-studio';

afterEach(cleanupFixtures);

describe('avatar-preset-picker', () => {
  it('fires exactly one ga-change per pick and supports arrow keys', async () => {
    const el = await fixture<AvatarPresetPicker>(
      html`<avatar-preset-picker value="Jay"></avatar-preset-picker>`,
    );
    const changes = recordEvents<GaChangeDetail>(el, 'ga-change');
    const radios = [...el.querySelectorAll<HTMLElement>('[role="radio"]')];
    radios[0].focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(changes.map((e) => e.detail.value)).toEqual(['Paul']);
    expect(el.value).toBe('Paul');
  });
});

describe('avatar-prompt-generator', () => {
  it('reports edits as avatar-prompt-change only (no leaked ga-change)', async () => {
    const wrapper = await fixture<HTMLDivElement>(
      html`<div><avatar-prompt-generator></avatar-prompt-generator></div>`,
    );
    const gaChanges = recordEvents(wrapper, 'ga-change');
    const prompts = recordEvents<AvatarPromptDetail>(
      wrapper,
      'avatar-prompt-change',
    );
    await userEvent.type(wrapper.querySelector('textarea, input')!, 'ab');
    expect(prompts.map((e) => e.detail.prompt)).toEqual(['a', 'ab']);
    expect(gaChanges).toHaveLength(0);
    await expectAccessible(wrapper);
  });
});

describe('avatar-upload-studio', () => {
  it('translates mode picks into avatar-transform-mode-change only', async () => {
    const wrapper = await fixture<HTMLDivElement>(
      html`<div><avatar-upload-studio transform-mode="avatar"></avatar-upload-studio></div>`,
    );
    const gaChanges = recordEvents(wrapper, 'ga-change');
    const modes = recordEvents<AvatarTransformModeChangeDetail>(
      wrapper,
      'avatar-transform-mode-change',
    );
    wrapper.querySelectorAll<HTMLElement>('[role="radio"]')[2].click();
    expect(modes.map((e) => e.detail.mode)).toEqual(['remove-bg']);
    expect(gaChanges).toHaveLength(0);
    expect(
      wrapper.querySelector('input[type="file"]')!.getAttribute('aria-label'),
    ).toBeTruthy();
    await expectAccessible(wrapper);
  });
});
