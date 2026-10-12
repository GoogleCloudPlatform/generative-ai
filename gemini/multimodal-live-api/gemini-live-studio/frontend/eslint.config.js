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

import tseslint from 'typescript-eslint';
import lit from 'eslint-plugin-lit';
import wc from 'eslint-plugin-wc';

export default tseslint.config(
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'public/**',
      'custom-elements.json',
    ],
  },
  ...tseslint.configs.recommended,
  wc.configs['flat/recommended'],
  lit.configs['flat/recommended'],
  {
    files: ['src/**/*.ts'],
    rules: {
      // Colours must come from tokens: no hex/rgb literals in components.
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Literal[value=/#[0-9a-fA-F]{3,8}\\b|rgba?\\(/]',
          message:
            'Use design tokens (Tailwind token classes or colorTokenReader) instead of raw colours.',
        },
        {
          selector:
            'TemplateElement[value.raw=/#[0-9a-fA-F]{6}\\b|rgba?\\(\\s*\\d/]',
          message:
            'Use design tokens (Tailwind token classes or colorTokenReader) instead of raw colours.',
        },
        {
          selector: 'CallExpression[callee.name=/^(alert|confirm|prompt)$/]',
          message: 'Use showToast() instead of blocking dialogs.',
        },
      ],
      'lit/no-invalid-html': 'error',
      'lit/attribute-value-entities': 'error',
      'lit/no-legacy-template-syntax': 'error',
      'lit/no-property-change-update': 'error',
      'wc/guard-super-call': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    // Token definitions and their generator are the one place raw colours live.
    files: [
      'src/theme/tokens.ts',
      'scripts/**',
      '*.config.*',
      'src/**/*.test.ts',
    ],
    rules: { 'no-restricted-syntax': 'off' },
  },
);
