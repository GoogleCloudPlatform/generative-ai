import '@google/genai';

declare module '@google/genai' {
  export interface GoogleGenAIPatch {
    apiClient: {
      isVertexAI?: () => boolean;
      getProject?: () => string;
      getLocation?: () => string;
    };
  }
}
