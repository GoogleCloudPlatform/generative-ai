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
