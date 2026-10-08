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
import './ga-field';
import type { GaField } from './ga-field';

afterEach(cleanupFixtures);

describe('ga-field', () => {
  it('links the label, supporting text and counter to the control', async () => {
    const el = await fixture<GaField>(
      html`<ga-field label="Name" supporting-text="Shown to users" max-length="10" value="abc"></ga-field>`,
    );
    const input = el.querySelector('input')!;
    expect(input.labels?.[0]?.textContent).toBe('Name');
    const describedBy = input.getAttribute('aria-describedby')!.split(' ');
    expect(
      describedBy.map((id) => document.getElementById(id)?.textContent?.trim()),
    ).toEqual(['Shown to users', expect.stringContaining('3 /')]);
    expect(input.maxLength).toBe(10);
    await expectAccessible(el);
  });

  it('hide-label keeps the accessible name', async () => {
    const el = await fixture<GaField>(
      html`<ga-field label="Message" hide-label></ga-field>`,
    );
    const label = el.querySelector('label')!;
    expect(label.classList.contains('sr-only')).toBe(true);
    expect(el.querySelector('input')!.labels?.[0]).toBe(label);
    await expectAccessible(el);
  });

  it('fires exactly one ga-change per edit, including number fields', async () => {
    const el = await fixture<GaField>(
      html`<ga-field label="Silence" type="number" min="0" max="5000"></ga-field>`,
    );
    const events = recordEvents<GaChangeDetail>(el, 'ga-change');
    const input = el.querySelector('input')!;
    await userEvent.type(input, '42');
    input.dispatchEvent(new Event('change', { bubbles: true }));
    expect(events.map((e) => e.detail.value)).toEqual(['4', '42']);
    expect(input.max).toBe('5000');
  });

  it('error-text marks the control invalid and describes it', async () => {
    const el = await fixture<GaField>(
      html`<ga-field label="Prompt" multiline error-text="Too long"></ga-field>`,
    );
    const ta = el.querySelector('textarea')!;
    expect(ta.getAttribute('aria-invalid')).toBe('true');
    expect(
      document.getElementById(ta.getAttribute('aria-describedby')!)
        ?.textContent,
    ).toBe('Too long');
    await expectAccessible(el);
  });

  it('gives each instance a distinct id', async () => {
    const el = await fixture<HTMLDivElement>(
      html`<div><ga-field label="A"></ga-field><ga-field label="B"></ga-field></div>`,
    );
    await Promise.all(
      [...el.querySelectorAll('ga-field')].map((f) => f.updateComplete),
    );
    const ids = [...el.querySelectorAll('input')].map((i) => i.id);
    expect(new Set(ids).size).toBe(2);
  });
});
