// /usr/local/google/home/switon/dev/quick-bot-app/multi-agent-skeleton/frontend/src/app/models/messegeType.model.ts
export interface ThinkingStep {
  type: 'functionCall' | 'functionResponse';
  name: string;
  data: any; // For args in functionCall, or response in functionResponse
}

export interface Message {
  body: string; // This will now primarily hold the final textual answer
  type: string;
  responseTime?: string;
  shareable: boolean;
  categoryIntent?: string;
  extras?: Extras;
  suggestedQuestion?: string[];
  botStartTime?: string;

  // Array to store all intermediate thinking steps for a single bot turn
  thinkingSteps?: ThinkingStep[];

  // We can remove these if all function/response details go into thinkingSteps
  // functionCall?: {
  //   name: string;
  //   args: any;
  // };
  // functionResponse?: {
  //   name: string;
  //   response: any;
  // };
}

export type Extras = {
  like: boolean;
  dislike: boolean;
  delete?: boolean;
};

export interface SuggestionData {
  suggestedQuestion: string[];
}
