// Copyright 2026 Google LLC
//
// Use of this source code is governed by an MIT-style
// license that can be found in the LICENSE file or at
// https://opensource.org/licenses/MIT.

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
