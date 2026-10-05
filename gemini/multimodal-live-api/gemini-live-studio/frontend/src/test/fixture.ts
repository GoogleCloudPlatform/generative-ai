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

import { render, type TemplateResult } from 'lit';
import axe from 'axe-core';
import '../index.css';

// Tests assert final states; CSS transitions would let axe sample
// mid-animation colours.
const noMotion = document.createElement('style');
noMotion.textContent =
  '*,*::before,*::after{transition:none!important;animation:none!important}';
document.head.append(noMotion);

const mounted: HTMLElement[] = [];

/**
 * Renders a Lit template into a fresh container attached to the document,
 * waits for every Lit element inside to finish updating, and returns the
 * first element child.
 */
export async function fixture<T extends Element = HTMLElement>(
  template: TemplateResult,
): Promise<T> {
  const container = document.createElement('div');
  document.body.append(container);
  mounted.push(container);
  render(template, container);
  await settle(container);
  return container.firstElementChild as T;
}

/** Waits for all Lit elements under `root` (and the root) to finish updating. */
export async function settle(root: Element): Promise<void> {
  const els = [root, ...root.querySelectorAll('*')] as Array<
    Element & { updateComplete?: Promise<unknown> }
  >;
  await Promise.all(els.map((el) => el.updateComplete));
}

/** Removes everything mounted by `fixture()`; call from afterEach. */
export function cleanupFixtures(): void {
  for (const el of mounted.splice(0)) el.remove();
}

/**
 * Accepted exception (design decision: keep the brand blue for fills): white text on the solid brand `primary` fill (#4285F4) is
 * 3.56:1, and white on the solid `success` fill is 3.30:1. Both pass 3:1
 * (large text / UI) but not 4.5:1. Primary-coloured *text* must use
 * `text-primary-text`, which is not exempt. Only colour-contrast is skipped
 * for these nodes; every other rule still runs on them.
 */
const KNOWN_CONTRAST_EXCEPTIONS = [
  '.bg-primary',
  '.bg-primary *',
  '.bg-nav',
  '.bg-nav *',
  '.bg-success.text-on-success',
];

/** Fails the test with a readable message if axe finds WCAG 2.x A/AA violations. */
export async function expectAccessible(root: Element): Promise<void> {
  const result = await axe.run(root, {
    runOnly: {
      type: 'tag',
      values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
    },
  });
  result.violations = result.violations
    .map((v) =>
      v.id === 'color-contrast'
        ? {
            ...v,
            nodes: v.nodes.filter(
              (n) =>
                !KNOWN_CONTRAST_EXCEPTIONS.some((sel) =>
                  document.querySelector(String(n.target[0]))?.matches(sel),
                ),
            ),
          }
        : v,
    )
    .filter((v) => v.nodes.length > 0);
  if (result.violations.length) {
    const msg = result.violations
      .map(
        (v) =>
          `${v.id} (${v.impact}): ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`,
      )
      .join('\n');
    throw new Error(
      `axe found ${result.violations.length} accessibility violation(s):\n${msg}`,
    );
  }
}

/** Collects events of `type` dispatched on (or bubbling through) `target`. */
export function recordEvents<D = unknown>(
  target: EventTarget,
  type: string,
): Array<CustomEvent<D>> {
  const seen: Array<CustomEvent<D>> = [];
  target.addEventListener(type, (e) => seen.push(e as CustomEvent<D>));
  return seen;
}
