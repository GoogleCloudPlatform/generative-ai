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
import {
  cleanupFixtures,
  expectAccessible,
  fixture,
  recordEvents,
} from '../../test/fixture';
import './ga-select';
import type { GaSelect } from './ga-select';

afterEach(cleanupFixtures);

const options = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Beta' },
];

describe('ga-select', () => {
  it('labels the native select and reports changes', async () => {
    const el = await fixture<GaSelect>(
      html`<ga-select label="Voice" supporting-text="Pick one" .options=${options} value="a"></ga-select>`,
    );
    const select = el.querySelector('select')!;
    expect(select.labels?.[0]?.textContent).toBe('Voice');
    expect(
      document.getElementById(select.getAttribute('aria-describedby')!)
        ?.textContent,
    ).toBe('Pick one');
    const events = recordEvents(el, 'ga-change');
    select.value = 'b';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    expect(events).toHaveLength(1);
    expect(el.value).toBe('b');
    await expectAccessible(el);
  });
});
