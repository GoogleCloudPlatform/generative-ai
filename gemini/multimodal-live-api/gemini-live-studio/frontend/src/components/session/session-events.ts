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
export type SessionAction =
  | 'toggle-mic'
  | 'toggle-camera'
  | 'toggle-screen'
  | 'toggle-mute'
  | 'end-session';

export interface SessionActionDetail {
  action: SessionAction;
}

export interface SessionSendTextDetail {
  text: string;
}

export function sessionActionEvent(
  action: SessionAction,
): CustomEvent<SessionActionDetail> {
  return new CustomEvent<SessionActionDetail>('session-action', {
    detail: { action },
    bubbles: true,
    composed: true,
  });
}

declare global {
  interface HTMLElementEventMap {
    'session-action': CustomEvent<SessionActionDetail>;
    'session-send-text': CustomEvent<SessionSendTextDetail>;
  }
}
