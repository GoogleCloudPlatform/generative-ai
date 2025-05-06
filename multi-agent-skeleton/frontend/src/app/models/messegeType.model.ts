// /usr/local/google/home/switon/dev/quick-bot-app/multi-agent-skeleton/frontend/src/app/models/messegeType.model.ts
export interface Message {
  body: string,
  botAnswer?: string, // This might become less relevant if body handles all text
  type: string,
  responseTime?: string
  shareable: boolean,
  categoryIntent?: string,
  extras?: Extras,
  suggestedQuestion?: string[],
  botStartTime?: string;
  chat_id?:string // This was for HTTP session, likely not used for WS bot messages now

  // New properties for function calls and responses
  functionCall?: {
    name: string;
    args: any;
  };
  functionResponse?: {
    name: string;
    response: any;
  };
}
export type Extras = {
  like:boolean,
  dislike:boolean,
  delete?: boolean
}

export interface SuggestionData {
  suggestedQuestion: string[]
}
