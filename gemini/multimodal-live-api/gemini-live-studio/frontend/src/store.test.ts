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
import { Store } from './store';

afterEach(() => localStorage.removeItem('gemini_avatar_settings'));

describe('Store theme', () => {
  it('defaults to light and keeps valid saved themes', () => {
    expect(Store.getSettings().theme).toBe('light');
    localStorage.setItem(
      'gemini_avatar_settings',
      JSON.stringify({ theme: 'system' }),
    );
    expect(Store.getSettings().theme).toBe('system');
  });

  it('falls back to light for unknown values', () => {
    localStorage.setItem(
      'gemini_avatar_settings',
      JSON.stringify({ theme: 'neon' }),
    );
    expect(Store.getSettings().theme).toBe('light');
  });
});
