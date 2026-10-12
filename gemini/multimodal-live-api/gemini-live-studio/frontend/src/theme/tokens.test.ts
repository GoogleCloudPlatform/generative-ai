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

import { describe, expect, it } from 'vitest';
import generated from './tokens.css?raw';
import { format } from 'prettier/standalone';
import * as postcss from 'prettier/plugins/postcss';
import {
  darkColors,
  hexToChannels,
  lightColors,
  readColorToken,
  tokenCss,
  type ColorToken,
} from './tokens';
import '../index.css';

function luminance(hex: string): number {
  const [r, g, b] = hexToChannels(hex)
    .split(' ')
    .map((v) => {
      const c = Number(v) / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Accepted sub-4.5:1 fill pairs (design decision: the brand blue stays for
// fills). Each must still meet 3:1. Text uses primary-text instead.
const CONTRAST_EXCEPTIONS: Partial<Record<'light' | 'dark', ColorToken[]>> = {
  light: ['primary', 'success', 'nav'],
};

describe('design tokens', () => {
  it('src/theme/tokens.css is up to date (run `npm run tokens`)', async () => {
    const expected = await format(tokenCss(), {
      parser: 'css',
      plugins: [postcss],
      singleQuote: true,
    });
    expect(generated).toBe(expected);
  });

  it('dark theme defines exactly the light theme keys', () => {
    expect(Object.keys(darkColors).sort()).toEqual(
      Object.keys(lightColors).sort(),
    );
  });

  it('every token is a 6-digit hex colour', () => {
    for (const v of [
      ...Object.values(lightColors),
      ...Object.values(darkColors),
    ]) {
      expect(v).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });

  for (const [theme, colors] of [
    ['light', lightColors],
    ['dark', darkColors],
  ] as const) {
    it(`${theme}: on-* text colours meet WCAG AA against their surface`, () => {
      const failures: string[] = [];
      for (const key of Object.keys(colors) as ColorToken[]) {
        if (!key.startsWith('on-')) continue;
        const bg = key.slice(3) as ColorToken;
        if (!(bg in colors)) continue;
        const ratio = contrast(colors[key], colors[bg]);
        const min = CONTRAST_EXCEPTIONS[theme]?.includes(bg) ? 3 : 4.5;
        if (ratio < min)
          failures.push(`${key} on ${bg}: ${ratio.toFixed(2)} < ${min}`);
      }
      expect(failures).toEqual([]);
    });
  }

  for (const [theme, colors] of [
    ['light', lightColors],
    ['dark', darkColors],
  ] as const) {
    it(`${theme}: primary-text meets AA on every surface`, () => {
      const surfaces: ColorToken[] = [
        'surface',
        'surface-container-lowest',
        'surface-container-low',
        'surface-container',
        'surface-container-high',
        'surface-container-highest',
      ];
      const failures = surfaces
        .map(
          (bg) => [bg, contrast(colors['primary-text'], colors[bg])] as const,
        )
        .filter(([, r]) => r < 4.5)
        .map(([bg, r]) => `${bg}: ${r.toFixed(2)}`);
      expect(failures).toEqual([]);
    });
  }

  it('data-theme switches the resolved custom properties', () => {
    const el = document.createElement('div');
    document.body.append(el);
    try {
      el.dataset.theme = 'light';
      expect(readColorToken(el, 'surface')).toBe(
        `rgb(${hexToChannels(lightColors.surface)} / 1)`,
      );
      el.dataset.theme = 'dark';
      expect(readColorToken(el, 'surface')).toBe(
        `rgb(${hexToChannels(darkColors.surface)} / 1)`,
      );
    } finally {
      el.remove();
    }
  });
});
