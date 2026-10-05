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
import './ga-button';
import type { GaButton } from './ga-button';

afterEach(cleanupFixtures);

describe('ga-button', () => {
  it('exposes active as aria-pressed only for toggle buttons', async () => {
    const plain = await fixture<GaButton>(
      html`<ga-button label="Save" active></ga-button>`,
    );
    expect(plain.querySelector('button')!.hasAttribute('aria-pressed')).toBe(
      false,
    );

    const toggle = await fixture<GaButton>(
      html`<ga-button variant="pill" icon="mic" accessible-label="Microphone" toggle></ga-button>`,
    );
    const btn = toggle.querySelector('button')!;
    expect(btn.getAttribute('aria-pressed')).toBe('false');
    toggle.active = true;
    await toggle.updateComplete;
    expect(btn.getAttribute('aria-pressed')).toBe('true');
    expect(btn.getAttribute('aria-label')).toBe('Microphone');
    await expectAccessible(toggle);
  });

  it('suppresses clicks while disabled or loading', async () => {
    const el = await fixture<GaButton>(
      html`<ga-button label="Go" loading></ga-button>`,
    );
    const clicks = recordEvents(el, 'click');
    el.click();
    expect(clicks).toHaveLength(0);
    el.loading = false;
    await el.updateComplete;
    el.click();
    expect(clicks).toHaveLength(1);
  });
});
