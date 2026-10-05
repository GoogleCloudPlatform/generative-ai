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
import { afterEach, describe, expect, it } from 'vitest';
import { html } from 'lit';
import { userEvent } from 'vitest/browser';
import { cleanupFixtures, expectAccessible, fixture } from '../../test/fixture';
import './ga-segmented-control';
import type { GaSegmentedControl } from './ga-segmented-control';

afterEach(cleanupFixtures);

const options = [
  { value: 'preset', label: 'Presets' },
  { value: 'upload', label: 'Upload' },
  { value: 'hidden', label: 'Hidden', hidden: true },
  { value: 'generate', label: 'Generate' },
];

describe('ga-segmented-control', () => {
  it('roving focus selects with arrows, Home and End', async () => {
    const el = await fixture<GaSegmentedControl>(
      html`<ga-segmented-control aria-label="Avatar source" .options=${options} value="preset"></ga-segmented-control>`,
    );
    const tabs = () => [...el.querySelectorAll<HTMLElement>('[role="tab"]')];
    expect(tabs().map((t) => t.tabIndex)).toEqual([0, -1, -1]);
    tabs()[0].focus();
    await userEvent.keyboard('{ArrowLeft}');
    expect(el.value).toBe('generate');
    await userEvent.keyboard('{Home}');
    expect(el.value).toBe('preset');
    await userEvent.keyboard('{ArrowRight}');
    expect(el.value).toBe('upload');
    await el.updateComplete;
    expect(tabs().map((t) => t.tabIndex)).toEqual([-1, 0, -1]);
    await expectAccessible(el);
  });
});
