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

export interface TranscriptToolCard {
  id?: string;
  name: string;
  title: string;
  summary: string;
  category?: string;
  items?: string[];
  cancelled?: boolean;
}

export interface TranscriptItem {
  type: 'user' | 'assistant' | 'tool';
  text: string;
  isPartial?: boolean;
  toolCard?: TranscriptToolCard;
}

/**
 * Parses a server `tool_call` JSON message into a structured `TranscriptItem`.
 */
export function parseToolCallItem(
  msg: Record<string, unknown>,
): TranscriptItem {
  const name = typeof msg.name === 'string' ? msg.name : 'tool';
  const id = typeof msg.id === 'string' ? msg.id : undefined;
  const args =
    msg.args && typeof msg.args === 'object'
      ? (msg.args as Record<string, unknown>)
      : {};
  const title =
    typeof args.title === 'string' && args.title.trim()
      ? args.title.trim()
      : name;
  const summary =
    typeof args.summary === 'string' && args.summary.trim()
      ? args.summary.trim()
      : JSON.stringify(args);
  const category =
    typeof args.category === 'string' && args.category.trim()
      ? args.category.trim()
      : undefined;
  const items = Array.isArray(args.items)
    ? args.items
        .filter(
          (it): it is string => typeof it === 'string' && it.trim() !== '',
        )
        .map((it) => it.trim())
    : undefined;

  return {
    type: 'tool',
    text: `${title}: ${summary}`,
    toolCard: {
      id,
      name,
      title,
      summary,
      category,
      items,
    },
  };
}

/**
 * Pure, immutable streaming transcript accumulator for Gemini Live user and
 * model speech turns plus tool cards and barge-in markers.
 */
export class TranscriptAssembler {
  entries: TranscriptItem[] = [];

  reset(): TranscriptItem[] {
    this.entries = [];
    return this.entries;
  }

  addUserText(text: string): TranscriptItem[] {
    this.entries = [...this.entries, { type: 'user', text }];
    return this.entries;
  }

  appendTurn(
    role: 'user' | 'assistant',
    text: string,
    isFinished: boolean,
    concatenatePartials: boolean,
  ): TranscriptItem[] {
    const lastIdx = this.entries.length - 1;
    if (
      lastIdx >= 0 &&
      this.entries[lastIdx].type === role &&
      this.entries[lastIdx].isPartial
    ) {
      const next = [...this.entries];
      next[lastIdx] = {
        type: role,
        text: concatenatePartials ? next[lastIdx].text + text : text,
        isPartial: !isFinished,
      };
      this.entries = next;
    } else {
      this.entries = [
        ...this.entries,
        { type: role, text, isPartial: !isFinished },
      ];
    }
    return this.entries;
  }

  addToolCall(msg: Record<string, unknown>): TranscriptItem[] {
    this.entries = [...this.entries, parseToolCallItem(msg)];
    return this.entries;
  }

  cancelToolCalls(ids: readonly string[]): TranscriptItem[] {
    const cancelledIds = new Set<string>(ids);
    this.entries = this.entries.map((entry) =>
      entry.type === 'tool' &&
      entry.toolCard?.id &&
      cancelledIds.has(entry.toolCard.id)
        ? {
            ...entry,
            toolCard: { ...entry.toolCard, cancelled: true },
          }
        : entry,
    );
    return this.entries;
  }

  markInterrupted(): boolean {
    if (this.entries.length === 0) return false;
    const last = this.entries[this.entries.length - 1];
    if (last.type !== 'assistant' || !last.isPartial) return false;
    const next = [...this.entries];
    next[next.length - 1] = {
      type: 'assistant',
      text: last.text + ' \u2014',
      isPartial: false,
    };
    this.entries = next;
    return true;
  }

  sealActiveTurns(): boolean {
    let changed = false;
    const next = this.entries.map((entry) => {
      if (entry.isPartial) {
        changed = true;
        return { ...entry, isPartial: false };
      }
      return entry;
    });
    if (changed) {
      this.entries = next;
    }
    return changed;
  }
}
