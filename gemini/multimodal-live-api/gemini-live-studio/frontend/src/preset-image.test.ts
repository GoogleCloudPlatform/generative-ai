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
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { cleanupFixtures, expectAccessible, fixture } from './test/fixture';
import { presetImageUrl, renderPresetThumb } from './preset-image';

@customElement('test-preset-thumb')
class TestPresetThumb extends LitElement {
  @property() name = '';
  protected override createRenderRoot() {
    return this;
  }
  protected override render() {
    return renderPresetThumb(this.name, this, 'w-10 h-10', 'w-10 h-10');
  }
}

afterEach(cleanupFixtures);

describe('presetImageUrl', () => {
  it('uses <name>.png, with per-preset overrides', () => {
    expect(presetImageUrl('Ben')).toMatch(/\/avatars\/ben\.png$/);
    expect(presetImageUrl('Carmen')).toMatch(/\/avatars\/carmen_2\.png$/);
  });
});

describe('renderPresetThumb', () => {
  it('replaces a missing image with a theme-aware initial', async () => {
    // A name whose CDN image is guaranteed missing; the request fails offline too.
    const el = await fixture<TestPresetThumb>(
      html`<test-preset-thumb name="Zz-missing"></test-preset-thumb>`,
    );
    const img = el.querySelector('img')!;
    await new Promise((r) => img.addEventListener('error', r, { once: true }));
    await el.updateComplete;
    const initial = el.querySelector('[role="img"]')!;
    expect(initial.textContent).toBe('Z');
    expect(initial.getAttribute('aria-label')).toBe('Zz-missing');
    expect(initial.className).toContain('bg-surface-container-highest');
    await expectAccessible(el);
  });
});
