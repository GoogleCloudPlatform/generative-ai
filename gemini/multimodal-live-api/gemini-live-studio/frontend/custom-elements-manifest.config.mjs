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

// Generates custom-elements.json (the documented public API of every ga-*,
// avatar-*, live-* and view element). `npm run manifest:check` fails if the
// checked-in file is stale.
export default {
  globs: ['src/**/*.ts'],
  exclude: ['src/**/*.test.ts', 'src/test/**'],
  outdir: '.',
  litelement: true,
  plugins: [
    {
      name: 'ga-sort-modules',
      // Analysis order depends on file-system order; sort for stable diffs.
      packageLinkPhase({ customElementsManifest }) {
        customElementsManifest.modules.sort((a, b) =>
          a.path.localeCompare(b.path),
        );
      },
    },
  ],
};
