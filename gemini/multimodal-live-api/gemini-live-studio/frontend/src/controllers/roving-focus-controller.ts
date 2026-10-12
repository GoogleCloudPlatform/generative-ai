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
import type { ReactiveController, ReactiveControllerHost } from 'lit';

export type RovingOrientation = 'horizontal' | 'vertical' | 'both';

export interface RovingFocusOptions {
  /** Returns the focusable items in DOM order (disabled items excluded). */
  items: () => HTMLElement[];
  /** Which arrow keys move focus. Default: 'both'. */
  orientation?: RovingOrientation;
  /** Called after focus moves via the keyboard (e.g. to select a radio). */
  onMove?: (item: HTMLElement, index: number) => void;
}

/**
 * Keyboard "roving tabindex" for composite widgets (radio groups, tab lists).
 *
 * Only one item is in the tab order (`tabindex="0"`); Arrow keys, Home and End
 * move focus between items, wrapping at the ends. Left/Right are mirrored in
 * right-to-left layouts. The host decides which item is current by calling
 * `sync(index)` after each render.
 */
export class RovingFocusController implements ReactiveController {
  private readonly host: ReactiveControllerHost & HTMLElement;
  private readonly options: Required<Omit<RovingFocusOptions, 'onMove'>> &
    Pick<RovingFocusOptions, 'onMove'>;

  constructor(
    host: ReactiveControllerHost & HTMLElement,
    options: RovingFocusOptions,
  ) {
    this.host = host;
    this.options = { orientation: 'both', ...options };
    host.addController(this);
  }

  hostConnected(): void {
    this.host.addEventListener('keydown', this.handleKeyDown);
  }

  hostDisconnected(): void {
    this.host.removeEventListener('keydown', this.handleKeyDown);
  }

  /** Puts item `index` (or the first item, if out of range) in the tab order. */
  sync(index: number): void {
    const items = this.options.items();
    const current = index >= 0 && index < items.length ? index : 0;
    items.forEach((item, i) => (item.tabIndex = i === current ? 0 : -1));
  }

  private readonly handleKeyDown = (e: KeyboardEvent) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const items = this.options.items();
    const from = items.findIndex(
      (item) => item === e.target || item.contains(e.target as Node),
    );
    if (from === -1) return;

    const next = this.nextIndex(e.key, from, items.length);
    if (next === null) return;
    e.preventDefault();
    const item = items[next];
    this.sync(next);
    item.focus();
    this.options.onMove?.(item, next);
  };

  private nextIndex(key: string, from: number, count: number): number | null {
    const { orientation } = this.options;
    const horizontal = orientation !== 'vertical';
    const vertical = orientation !== 'horizontal';
    const rtl = getComputedStyle(this.host).direction === 'rtl';
    const forward = rtl ? 'ArrowLeft' : 'ArrowRight';
    const backward = rtl ? 'ArrowRight' : 'ArrowLeft';

    if ((horizontal && key === forward) || (vertical && key === 'ArrowDown'))
      return (from + 1) % count;
    if ((horizontal && key === backward) || (vertical && key === 'ArrowUp'))
      return (from - 1 + count) % count;
    if (key === 'Home') return 0;
    if (key === 'End') return count - 1;
    return null;
  }
}
