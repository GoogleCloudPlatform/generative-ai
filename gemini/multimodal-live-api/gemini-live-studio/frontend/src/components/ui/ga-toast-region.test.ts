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
import { cleanupFixtures, expectAccessible, fixture } from '../../test/fixture';
import { showToast } from '../../theme/events';
import './ga-toast-region';
import type { GaToastRegion } from './ga-toast-region';

afterEach(cleanupFixtures);

describe('ga-toast-region', () => {
  it('keeps both live regions in the DOM before any toast', async () => {
    const el = await fixture<GaToastRegion>(
      html`<ga-toast-region></ga-toast-region>`,
    );
    expect(
      el.querySelector('[role="status"][aria-live="polite"]'),
    ).not.toBeNull();
    expect(
      el.querySelector('[role="alert"][aria-live="assertive"]'),
    ).not.toBeNull();
  });

  it('routes danger toasts to the alert region and others to status', async () => {
    const el = await fixture<GaToastRegion>(
      html`<ga-toast-region></ga-toast-region>`,
    );
    showToast('Saved', 'success');
    showToast('Microphone blocked', 'danger');
    await el.updateComplete;
    expect(el.querySelector('[role="status"]')!.textContent).toContain('Saved');
    expect(el.querySelector('[role="alert"]')!.textContent).toContain(
      'Microphone blocked',
    );
    await expectAccessible(el);
  });
});
