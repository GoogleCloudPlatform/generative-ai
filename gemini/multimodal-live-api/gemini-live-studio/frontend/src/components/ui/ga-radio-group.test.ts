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
import './ga-radio-group';
import type { GaRadioGroup } from './ga-radio-group';

afterEach(cleanupFixtures);

const options = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Beta', disabled: true },
  { value: 'c', label: 'Gamma' },
];

const radios = (el: Element) => [
  ...el.querySelectorAll<HTMLElement>('[role="radio"]'),
];

describe('ga-radio-group', () => {
  for (const appearance of ['chip', 'tile', 'card'] as const) {
    it(`${appearance}: is a labelled radiogroup with one tab stop`, async () => {
      const el = await fixture<GaRadioGroup>(
        html`<ga-radio-group label="Persona" appearance=${appearance} .options=${options} value="c"></ga-radio-group>`,
      );
      const group = el.querySelector('[role="radiogroup"]')!;
      expect(
        document.getElementById(group.getAttribute('aria-labelledby')!)
          ?.textContent,
      ).toBe('Persona');
      expect(radios(el).map((r) => r.tabIndex)).toEqual([-1, -1, 0]);
      expect(radios(el).map((r) => r.getAttribute('aria-checked'))).toEqual([
        'false',
        'false',
        'true',
      ]);
      await expectAccessible(el);
    });
  }

  it('arrow keys move and select, skipping disabled options and wrapping', async () => {
    const el = await fixture<GaRadioGroup>(
      html`<ga-radio-group label="P" .options=${options} value="a"></ga-radio-group>`,
    );
    const events = recordEvents<GaChangeDetail>(el, 'ga-change');
    radios(el)[0].focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(el.value).toBe('c');
    expect(document.activeElement).toBe(radios(el)[2]);
    await userEvent.keyboard('{ArrowDown}');
    expect(el.value).toBe('a');
    await userEvent.keyboard('{End}');
    expect(el.value).toBe('c');
    expect(events.map((e) => e.detail.value)).toEqual(['c', 'a', 'c']);
    await el.updateComplete;
    expect(radios(el).map((r) => r.tabIndex)).toEqual([-1, -1, 0]);
  });

  it('mirrors left/right in RTL', async () => {
    const el = await fixture<GaRadioGroup>(
      html`<ga-radio-group dir="rtl" label="P" .options=${options} value="a"></ga-radio-group>`,
    );
    radios(el)[0].focus();
    await userEvent.keyboard('{ArrowLeft}');
    expect(el.value).toBe('c');
  });

  it('click selects; clicking a disabled option does nothing', async () => {
    const el = await fixture<GaRadioGroup>(
      html`<ga-radio-group label="P" .options=${options} value="a"></ga-radio-group>`,
    );
    radios(el)[1].click();
    expect(el.value).toBe('a');
    radios(el)[2].click();
    expect(el.value).toBe('c');
  });

  it('programmatic value changes do not fire ga-change', async () => {
    const el = await fixture<GaRadioGroup>(
      html`<ga-radio-group label="P" .options=${options} value="a"></ga-radio-group>`,
    );
    const events = recordEvents(el, 'ga-change');
    el.value = 'c';
    await el.updateComplete;
    expect(events).toHaveLength(0);
    expect(radios(el)[2].tabIndex).toBe(0);
  });

  it('tile: shows fallback text when an image fails to load', async () => {
    const el = await fixture<GaRadioGroup>(
      html`<ga-radio-group
        label="Preset"
        appearance="tile"
        .options=${[{ value: 'c', label: 'Carmen', imageSrc: '/does-not-exist.png', imageFallbackText: 'C' }]}
      ></ga-radio-group>`,
    );
    await new Promise((r) =>
      el.querySelector('img')!.addEventListener('error', r, { once: true }),
    );
    await el.updateComplete;
    expect(el.querySelector('img')).toBeNull();
    expect(radios(el)[0].textContent).toContain('C');
    await expectAccessible(el);
  });
});
