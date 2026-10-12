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

import { LitElement, html, nothing, type PropertyValues } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { renderIcon } from '../ui/icons';
import '../ui/ga-badge';

export interface ToolCallCardData {
  id?: string;
  name: string;
  title: string;
  summary: string;
  category?: string;
  items?: string[];
  cancelled?: boolean;
}

export interface TranscriptEntry {
  type: 'user' | 'assistant' | 'tool';
  text: string;
  isPartial?: boolean;
  toolCard?: ToolCallCardData;
}

export function parseToolCallEntry(
  msg: Record<string, unknown>,
): TranscriptEntry {
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
 * Conversation transcript (`<session-transcript-panel>`) shared by avatar and
 * live sessions: user and assistant turns plus function-calling info cards.
 *
 * The list is a `role="log"`; while the newest entry is still streaming it is
 * marked `aria-busy` so screen readers announce whole turns, not every
 * partial transcript update.
 */
@customElement('session-transcript-panel')
export class SessionTranscriptPanel extends LitElement {
  @property({ attribute: false }) entries: readonly TranscriptEntry[] = [];
  @property({ type: String, attribute: 'assistant-label' }) assistantLabel =
    'gemini';

  protected override createRenderRoot() {
    return this;
  }

  protected override updated(changed: PropertyValues): void {
    if (changed.has('entries')) {
      const container = this.querySelector('#chat-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }

  private renderToolCard(card: ToolCallCardData) {
    return html`
      <div
        class="w-full rounded-2xl border border-primary/30 bg-surface-container-low p-4 shadow-sm flex flex-col gap-2.5 ${
          card.cancelled ? 'opacity-60' : ''
        }"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="w-6 h-6 rounded-lg bg-primary-soft text-on-primary-soft flex items-center justify-center shrink-0"
            >
              ${renderIcon('bolt', 'w-3.5 h-3.5')}
            </span>
            <span class="font-bold text-sm text-on-surface truncate">
              ${card.title}
            </span>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            ${
              card.category
                ? html`<ga-badge
                  label="${card.category}"
                  tone="primary"
                  pill
                ></ga-badge>`
                : nothing
            }
            ${
              card.cancelled
                ? html`<ga-badge
                  label="Cancelled"
                  tone="danger"
                  pill
                ></ga-badge>`
                : nothing
            }
          </div>
        </div>

        <p class="text-xs text-on-surface-variant leading-relaxed">
          ${card.summary}
        </p>

        ${
          card.items && card.items.length > 0
            ? html`
              <ul
                class="flex flex-col gap-1 text-xs text-on-surface pl-4 list-disc"
              >
                ${card.items.map((item) => html`<li>${item}</li>`)}
              </ul>
            `
            : nothing
        }

        <div
          class="pt-1.5 border-t border-outline-variant/20 flex items-center justify-between text-[10px] font-mono text-on-surface-variant"
        >
          <span>fn: ${card.name}</span>
          <span>${card.cancelled ? 'Interrupted' : 'Displayed'}</span>
        </div>
      </div>
    `;
  }

  protected override render() {
    return html`
      <div class="flex flex-col h-full min-h-0">
        <div class="p-6 border-b border-outline-variant/20 bg-surface shrink-0">
          <h3 class="font-bold text-on-surface">Live Transcript</h3>
        </div>

        <div
          id="chat-container"
          role="log"
          aria-label="Live transcript"
          aria-busy="${this.entries.at(-1)?.isPartial ? 'true' : 'false'}"
          class="flex-1 overflow-y-auto p-6 flex flex-col gap-4 min-h-0"
        >
          ${
            this.entries.length === 0
              ? html`
                <div
                  class="flex flex-col items-center justify-center h-full text-on-surface-variant gap-3"
                >
                  ${renderIcon('chat', 'w-8 h-8')}
                  <span class="text-sm font-medium">No messages yet</span>
                </div>
              `
              : nothing
          }
          ${this.entries.map((msg) =>
            msg.type === 'tool' && msg.toolCard
              ? this.renderToolCard(msg.toolCard)
              : html`
                  <div
                    class="flex flex-col ${
                      msg.type === 'user' ? 'items-end' : 'items-start'
                    }"
                  >
                    <span
                      class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1 px-1"
                    >
                      ${msg.type === 'user' ? 'user' : this.assistantLabel}
                    </span>
                    <div
                      class="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.type === 'user'
                          ? 'bg-primary text-on-primary rounded-tr-sm'
                          : 'bg-surface-container-low text-on-surface rounded-tl-sm'
                      }"
                    >
                      ${msg.text}
                    </div>
                  </div>
                `,
          )}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'session-transcript-panel': SessionTranscriptPanel;
  }
}
