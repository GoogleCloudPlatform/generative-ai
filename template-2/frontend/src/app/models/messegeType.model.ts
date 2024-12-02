export interface Message {
  body: string,
  botAnswer?: string,
  type: string,
  responseTime?: string
  shareable: boolean,
  categoryIntent?: string,
  extras?: Extras,
  suggestedQuestion?: string[],
  botStartTime?: string;
  chat_id?:string
}
export type Extras = {
  like:boolean,
  dislike:boolean,
  delete?: boolean
}

export interface SuggestionData {
  suggestedQuestion: string[]
}
