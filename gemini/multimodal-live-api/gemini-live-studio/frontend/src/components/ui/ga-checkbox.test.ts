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
import {
  cleanupFixtures,
  expectAccessible,
  fixture,
  recordEvents,
} from '../../test/fixture';
import type { GaChangeDetail } from '../../theme/events';
import './ga-checkbox';
import type { GaCheckbox } from './ga-checkbox';

afterEach(cleanupFixtures);

describe('ga-checkbox', () => {
  it('is labelled, described, and toggles from the whole card', async () => {
    const el = await fixture<GaCheckbox>(
      html`<ga-checkbox label="Google Search" description="Live web grounding" icon="globe"></ga-checkbox>`,
    );
    const input = el.querySelector('input')!;
    expect(input.labels?.[0]?.textContent).toContain('Google Search');
    expect(
      document
        .getElementById(input.getAttribute('aria-describedby')!)
        ?.textContent?.trim(),
    ).toBe('Live web grounding');
    const events = recordEvents<GaChangeDetail>(el, 'ga-change');
    await userEvent.click(el.querySelector('label')!);
    expect(el.checked).toBe(true);
    expect(events.map((e) => e.detail)).toEqual([
      { value: 'true', checked: true },
    ]);
    await userEvent.keyboard(' ');
    expect(el.checked).toBe(false);
    await expectAccessible(el);
  });

  it('does not toggle when disabled', async () => {
    const el = await fixture<GaCheckbox>(
      html`<ga-checkbox label="Off" disabled></ga-checkbox>`,
    );
    const events = recordEvents(el, 'ga-change');
    el.querySelector('label')!.click();
    expect(events).toHaveLength(0);
  });
});
