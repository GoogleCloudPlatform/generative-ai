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
/** User intents emitted by shared session components as `session-action`. */
import { afterEach, describe, expect, it } from 'vitest';
import { html } from 'lit';
import { userEvent } from 'vitest/browser';
import {
  cleanupFixtures,
  expectAccessible,
  fixture,
  recordEvents,
} from '../../test/fixture';
import './index';
import type {
  SessionActionDetail,
  SessionSendTextDetail,
} from './session-events';
import type { SessionControlBar } from './session-control-bar';
import type { SessionStageHeader } from './session-stage-header';
import type { SessionTranscriptPanel } from './session-transcript-panel';

afterEach(cleanupFixtures);

describe('session-control-bar', () => {
  it('emits one session-action per button and exposes toggles as aria-pressed', async () => {
    const el = await fixture<SessionControlBar>(
      html`<session-control-bar camera-active></session-control-bar>`,
    );
    const actions = recordEvents<SessionActionDetail>(el, 'session-action');
    const buttons = [...el.querySelectorAll('button')];
    for (const b of buttons) b.click();
    expect(actions.map((e) => e.detail.action)).toEqual([
      'toggle-camera',
      'toggle-screen',
      'end-session',
      'toggle-mic',
    ]);
    expect(buttons.map((b) => b.getAttribute('aria-pressed'))).toEqual([
      'true',
      'false',
      null,
      'false',
    ]);
    await expectAccessible(el);
  });

  it('sends trimmed text on Enter and clears the input', async () => {
    const el = await fixture<SessionControlBar>(
      html`<session-control-bar></session-control-bar>`,
    );
    const sent = recordEvents<SessionSendTextDetail>(el, 'session-send-text');
    const input = el.querySelector('input')!;
    await userEvent.type(input, '  hello  {Enter}');
    expect(sent.map((e) => e.detail.text)).toEqual(['hello']);
    expect(input.value).toBe('');
  });

  it('disables End Session while terminating', async () => {
    const el = await fixture<SessionControlBar>(
      html`<session-control-bar terminating></session-control-bar>`,
    );
    const actions = recordEvents(el, 'session-action');
    el.querySelector<HTMLElement>('ga-button[variant="danger-tonal"]')!.click();
    expect(actions).toHaveLength(0);
  });
});

describe('session-stage-header', () => {
  it('shows the voice as text, or as a mute toggle with mute-toggle', async () => {
    const plain = await fixture<SessionStageHeader>(
      html`<session-stage-header status="Connected" voice-name="Kore" session-model="gemini-3.8-live"></session-stage-header>`,
    );
    expect(plain.textContent).toContain('Kore Voice');
    expect(plain.querySelector('button')).toBeNull();

    const toggle = await fixture<SessionStageHeader>(
      html`<session-stage-header mute-toggle voice-name="Kore"></session-stage-header>`,
    );
    const actions = recordEvents<SessionActionDetail>(toggle, 'session-action');
    const btn = toggle.querySelector('button')!;
    expect(btn.getAttribute('aria-pressed')).toBe('false');
    btn.click();
    expect(actions.map((e) => e.detail.action)).toEqual(['toggle-mute']);
    await expectAccessible(toggle);
  });
});

describe('session-transcript-panel', () => {
  it('is a log that is busy while the last turn is streaming', async () => {
    const el = await fixture<SessionTranscriptPanel>(
      html`<session-transcript-panel></session-transcript-panel>`,
    );
    el.entries = [
      { type: 'user', text: 'Hi' },
      { type: 'assistant', text: 'Hel', isPartial: true },
    ];
    await el.updateComplete;
    const log = el.querySelector('[role="log"]')!;
    expect(log.getAttribute('aria-busy')).toBe('true');
    expect(log.textContent).toContain('gemini');
    el.entries = [
      ...el.entries.slice(0, 1),
      { type: 'assistant', text: 'Hello' },
    ];
    await el.updateComplete;
    expect(log.getAttribute('aria-busy')).toBe('false');
  });
});
