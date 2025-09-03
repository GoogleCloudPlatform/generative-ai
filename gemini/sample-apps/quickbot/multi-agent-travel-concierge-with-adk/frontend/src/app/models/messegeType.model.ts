/**
 * Copyright 2025 Google LLC
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

export interface ThinkingStep {
  type: 'functionCall' | 'functionResponse';
  name: string;
  data: any; // For args in functionCall, or response in functionResponse
}

// New interface to represent a part of the message content
export interface MessageContentPart {
  type: 'text' | 'thinking';
  text?: string; // For 'text' type
  thinkingSteps?: ThinkingStep[]; // For 'thinking' type
}

export interface Message {
  // body: string; // We might deprecate this or use it as a summary. For now, contentParts is primary.
  contentParts: MessageContentPart[]; // Array to hold the sequence of text and thinking blocks
  type: string;
  responseTime?: string;
  shareable: boolean;
  categoryIntent?: string;
  extras?: Extras;
  suggestedQuestion?: string[];
  botStartTime?: string;
}

export type Extras = {
  like: boolean;
  dislike: boolean;
  delete?: boolean;
};

export interface SuggestionData {
  suggestedQuestion: string[];
}
