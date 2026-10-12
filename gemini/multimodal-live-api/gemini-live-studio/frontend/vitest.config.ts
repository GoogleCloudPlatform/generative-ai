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

import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';

// Component tests run in a real (headless) Chromium so Lit rendering, focus,
// keyboard handling and axe checks behave as in the app. CHROMIUM_PATH lets
// environments without Playwright's downloaded browser use a system Chromium
// (e.g. CHROMIUM_PATH=/usr/bin/chromium); otherwise run
// `npx playwright install chromium` once.
const executablePath = process.env.CHROMIUM_PATH || undefined;

export default defineConfig({
  // Pre-bundle up front so Vite doesn't reload the browser mid-run.
  optimizeDeps: {
    include: [
      'lit',
      'lit/decorators.js',
      'lit/directives/if-defined.js',
      'axe-core',
      'prettier/standalone',
      'prettier/plugins/postcss',
    ],
  },
  test: {
    include: ['src/**/*.test.ts'],
    browser: {
      enabled: true,
      headless: true,
      provider: playwright({ launchOptions: { executablePath } }),
      instances: [{ browser: 'chromium' }],
    },
  },
});
