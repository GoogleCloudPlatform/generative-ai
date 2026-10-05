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

// Writes src/theme/tokens.css from src/theme/tokens.ts.
// Run with `npm run tokens` (Node >= 22.18 strips TypeScript types natively).
import { writeFileSync } from 'node:fs';
import { format } from 'prettier';
import { fileURLToPath } from 'node:url';
import { tokenCss } from '../src/theme/tokens.ts';

const out = fileURLToPath(new URL('../src/theme/tokens.css', import.meta.url));
// Formatted with the repo's Prettier settings so the file passes format checks.
writeFileSync(
  out,
  await format(tokenCss(), { parser: 'css', singleQuote: true }),
);
console.log(`wrote ${out}`);
