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
import './ga-section-header';
import type { GaSectionHeader } from './ga-section-header';

afterEach(cleanupFixtures);

describe('ga-section-header', () => {
  it('renders the heading level for its size and fires ga-action', async () => {
    const page = await fixture<GaSectionHeader>(
      html`<ga-section-header size="page" heading="Settings" subheading="Configure"></ga-section-header>`,
    );
    expect(page.querySelector('h2')?.textContent).toBe('Settings');

    const section = await fixture<GaSectionHeader>(
      html`<ga-section-header heading="Voice Detection" action-label="Reset to defaults"></ga-section-header>`,
    );
    expect(section.querySelector('h3')?.textContent).toBe('Voice Detection');
    const actions = recordEvents(section, 'ga-action');
    section.querySelector('button')!.click();
    expect(actions).toHaveLength(1);
    await expectAccessible(section);
  });
});
