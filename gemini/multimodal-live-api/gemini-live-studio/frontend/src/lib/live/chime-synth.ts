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

export type ChimePreset = 'soft' | 'subtle' | 'off';

export interface ChimePresetParams {
  readonly cutoffHz: number;
  readonly peakGain: number;
  readonly durationSec: number;
  readonly includeUpperFourth: boolean;
}

export const CHIME_PRESETS: Record<
  Exclude<ChimePreset, 'off'>,
  ChimePresetParams
> = {
  soft: {
    cutoffHz: 780,
    peakGain: 0.032,
    durationSec: 0.85,
    includeUpperFourth: true,
  },
  subtle: {
    cutoffHz: 620,
    peakGain: 0.014,
    durationSec: 0.55,
    includeUpperFourth: false,
  },
};

export function normalizeChimePreset(
  value: string | null | undefined,
  fallback: ChimePreset = 'soft',
): ChimePreset {
  const v = (value ?? '').trim().toLowerCase();
  if (v === 'soft' || v === 'subtle' || v === 'off') return v;
  return fallback;
}

/**
 * Synthesizes warm, non-intrusive procedural Web Audio cues (392 Hz G4 sine
 * fundamental with an optional 523.25 Hz C5 overtone through a gentle low-pass
 * filter) without shipping external audio assets.
 */
export class ChimeSynth {
  mode: ChimePreset;

  constructor(initialMode: ChimePreset = 'soft') {
    this.mode = initialMode;
  }

  setMode(mode: ChimePreset): void {
    this.mode = mode;
  }

  cycleMode(): ChimePreset {
    const order: readonly ChimePreset[] = ['soft', 'subtle', 'off'];
    const idx = order.indexOf(this.mode);
    this.mode = order[(idx + 1) % order.length];
    return this.mode;
  }

  /**
   * Plays an ambient alert cue on `ctx` and returns its duration in seconds
   * (0 when `mode === 'off'`).
   */
  playAmbientCue(ctx: AudioContext): number {
    if (this.mode === 'off') return 0;
    const params = CHIME_PRESETS[this.mode];
    const now = ctx.currentTime;

    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(params.cutoffHz, now);
    filter.Q.setValueAtTime(0.7, now);

    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(0.0001, now);
    masterGain.gain.exponentialRampToValueAtTime(params.peakGain, now + 0.06);
    masterGain.gain.exponentialRampToValueAtTime(
      0.0001,
      now + params.durationSec,
    );

    const osc1 = ctx.createOscillator();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(392.0, now);
    osc1.connect(filter);

    let osc2: OscillatorNode | null = null;
    if (params.includeUpperFourth) {
      osc2 = ctx.createOscillator();
      const upperGain = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(523.25, now);
      upperGain.gain.setValueAtTime(0.45, now);
      osc2.connect(upperGain);
      upperGain.connect(filter);
    }

    filter.connect(masterGain);
    masterGain.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + params.durationSec + 0.05);
    if (osc2) {
      osc2.start(now + 0.03);
      osc2.stop(now + params.durationSec + 0.05);
    }
    return params.durationSec;
  }

  /**
   * Plays a brief single-note confirmation tone (`392 Hz` low-passed sine).
   */
  playTurnTone(ctx: AudioContext): number {
    if (this.mode === 'off') return 0;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const filter = ctx.createBiquadFilter();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(392.0, now);
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(680, now);

    const peak = this.mode === 'subtle' ? 0.01 : 0.02;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(peak, now + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.45);
    return 0.4;
  }
}
