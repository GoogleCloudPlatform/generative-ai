/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import type { Config } from 'tailwindcss';
import { colorVar, lightColors, type ColorToken } from './src/theme/tokens.ts';

// Every colour comes from src/theme/tokens.ts and resolves through a
// --ga-color-* custom property, so classes follow data-theme and opacity
// modifiers (bg-primary/10) keep working.
const colors = Object.fromEntries(
  (Object.keys(lightColors) as ColorToken[]).map((name) => [
    name,
    `rgb(var(${colorVar(name)}) / <alpha-value>)`,
  ]),
);

export default {
  content: ['./index.html', './src/**/*.ts'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--ga-font-sans)'],
        mono: ['var(--ga-font-mono)'],
      },
      colors,
    },
  },
  plugins: [],
} satisfies Config;
