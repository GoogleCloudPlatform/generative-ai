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
import {
  CHIME_PRESETS,
  ChimeSynth,
  TranscriptAssembler,
  WebmcpToolHost,
  computeInt16Rms,
  describeCloseEvent,
  int16ArrayToLittleEndianBytes,
  normalizeChimePreset,
  uint8ArrayToBase64,
  type ModelContextLike,
  type WebmcpRegisteredTool,
} from './index';

describe('TranscriptAssembler', () => {
  it('accumulates assistant partials, replaces user partials, and marks barge-in', () => {
    const t = new TranscriptAssembler();

    t.appendTurn('user', 'hello', false, false);
    t.appendTurn('user', 'hello there', true, false);
    expect(t.entries).toEqual([
      { type: 'user', text: 'hello there', isPartial: false },
    ]);

    t.appendTurn('assistant', 'Hi ', false, true);
    t.appendTurn('assistant', 'how can I ', false, true);
    expect(t.entries[1]).toEqual({
      type: 'assistant',
      text: 'Hi how can I ',
      isPartial: true,
    });

    expect(t.markInterrupted()).toBe(true);
    expect(t.entries[1]).toEqual({
      type: 'assistant',
      text: 'Hi how can I  \u2014',
      isPartial: false,
    });
    expect(t.markInterrupted()).toBe(false);
  });

  it('tracks tool call cards and marks cancelled IDs', () => {
    const t = new TranscriptAssembler();
    t.addToolCall({
      id: 'call-9',
      name: 'show_info_card',
      args: {
        title: 'Latency',
        summary: '2.45s TTFF on 3.8 Live',
        category: 'Metrics',
        items: ['24 kHz PCM', 'fMP4 muxed'],
      },
    });
    expect(t.entries[0].toolCard?.cancelled).toBeUndefined();

    t.cancelToolCalls(['call-9']);
    expect(t.entries[0].toolCard?.cancelled).toBe(true);
  });
});

describe('describeCloseEvent', () => {
  it('maps RFC 6455 close codes and suppresses clean termination', () => {
    expect(
      describeCloseEvent(1000, 'Session terminated', {
        limitReachedAlreadySurfaced: false,
        isTerminating: true,
        hadErrorEvent: false,
      }),
    ).toBeNull();

    expect(
      describeCloseEvent(1007, 'Invalid session config', {
        limitReachedAlreadySurfaced: false,
        isTerminating: false,
        hadErrorEvent: false,
      }),
    ).toEqual({ kind: 'invalid_config', message: 'Invalid session config' });

    expect(
      describeCloseEvent(1009, '', {
        limitReachedAlreadySurfaced: false,
        isTerminating: false,
        hadErrorEvent: false,
      })?.kind,
    ).toBe('too_large');

    expect(
      describeCloseEvent(1000, 'Session limit reached', {
        limitReachedAlreadySurfaced: true,
        isTerminating: false,
        hadErrorEvent: false,
      }),
    ).toBeNull();
  });
});

describe('PCM & Chime helpers', () => {
  it('encodes little-endian Int16 PCM and computes RMS bounds', () => {
    const samples = new Int16Array([0, 16384, -16384]);
    const bytes = int16ArrayToLittleEndianBytes(samples);
    expect(bytes.byteLength).toBe(6);
    expect(uint8ArrayToBase64(bytes).length).toBeGreaterThan(0);

    const rms = computeInt16Rms(samples);
    expect(rms).toBeGreaterThan(0.35);
    expect(rms).toBeLessThan(0.5);
  });

  it('normalizes and cycles chime presets', () => {
    expect(normalizeChimePreset('SUBTLE')).toBe('subtle');
    expect(normalizeChimePreset('invalid')).toBe('soft');

    const synth = new ChimeSynth('soft');
    expect(CHIME_PRESETS.soft.peakGain).toBeGreaterThan(
      CHIME_PRESETS.subtle.peakGain,
    );
    expect(synth.cycleMode()).toBe('subtle');
    expect(synth.cycleMode()).toBe('off');
    expect(synth.cycleMode()).toBe('soft');
  });
});

describe('WebmcpToolHost', () => {
  it('coalesces concurrent identical in-flight tool calls when enabled', async () => {
    let invocations = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    const host = new WebmcpToolHost((signal) => ({ signal }), null);
    await host.register([
      {
        name: 'upload_image',
        description: 'Prompt the user to upload an image',
        inputSchema: {
          type: 'object',
          properties: { title: { type: 'string' } },
        },
        coalesceInFlight: true,
        execute: async (args) => {
          invocations++;
          await gate;
          return { result: { uploaded: true, title: args.title ?? 'default' } };
        },
      },
    ]);

    const ac = new AbortController();
    const p1 = host.call('upload_image', { title: 'hero' }, ac.signal, 'live');
    const p2 = host.call('upload_image', { title: 'hero' }, ac.signal, 'live');

    release();
    const [r1, r2] = await Promise.all([p1, p2]);
    expect(invocations).toBe(1);
    expect(r1).toEqual({ uploaded: true, title: 'hero' });
    expect(r2).toEqual({ uploaded: true, title: 'hero' });
  });

  it('verifies ownership and negotiates string-form executeTool arguments', async () => {
    const stored = new Map<
      string,
      {
        reg: WebmcpRegisteredTool;
        exec: (input: Record<string, unknown> | string) => Promise<unknown>;
      }
    >();
    const fakeMc: ModelContextLike = Object.assign(new EventTarget(), {
      async registerTool(t: {
        name: string;
        description: string;
        inputSchema?: Record<string, unknown>;
        execute: (input: Record<string, unknown> | string) => Promise<unknown>;
      }) {
        stored.set(t.name, {
          reg: {
            name: t.name,
            description: t.description,
            // Emulate Chrome 154 returning serialized JSON schema strings:
            inputSchema: JSON.stringify(t.inputSchema ?? {}),
          },
          exec: t.execute,
        });
      },
      async getTools() {
        return [
          ...Array.from(stored.values()).map((s) => s.reg),
          {
            name: 'foreign_injected_tool',
            description: 'Not ours',
            inputSchema: '{}',
          },
        ];
      },
      async executeTool(
        tool: WebmcpRegisteredTool,
        input: Record<string, unknown> | string,
      ) {
        if (typeof input !== 'string') {
          throw new TypeError('Failed to parse input arguments');
        }
        const entry = stored.get(tool.name);
        const out = await entry!.exec(input);
        return JSON.stringify(out);
      },
    });

    const host = new WebmcpToolHost((signal) => ({ signal }), fakeMc);
    await host.register([
      {
        name: 'list_assets',
        description: 'Lists board assets',
        inputSchema: { type: 'object', properties: {} },
        readOnly: true,
        execute: async () => ({ result: { count: 3 } }),
      },
    ]);

    const listed = await host.list();
    expect(listed.map((t) => t.name)).toEqual(['list_assets']);
    expect(host.diagnostics.dropped.length).toBe(1);

    const res = await host.call(
      'list_assets',
      {},
      new AbortController().signal,
    );
    expect(res).toEqual({ count: 3 });
    expect(host.diagnostics.argsForm).toBe('string');

    const refused = await host.call(
      'foreign_injected_tool',
      {},
      new AbortController().signal,
    );
    expect(refused.error).toContain('not registered by this app');
  });
});
