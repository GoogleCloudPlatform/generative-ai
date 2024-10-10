/**
 * Copyright 2024 Google LLC
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

import { makeGroundingSearchSource } from '@/lib/grounding_option_utils';

const responseCandidateToResult = (candidate: any) => {
  let result: any = {};

  if (
    candidate.content &&
    candidate.content.parts &&
    candidate.content.parts[0] &&
    candidate.content.parts[0].text
  ) {
    result.text = candidate.content.parts[0].text;
  }

  if (candidate.groundingMetadata && candidate.groundingMetadata.searchEntryPoint) {
    result.searchEntryPoint =
      candidate.groundingMetadata.searchEntryPoint.renderedContent;
  }

  if (candidate.groundingMetadata && candidate.groundingMetadata.groundingSupport) {
    result.groundingSupport = candidate.groundingMetadata.groundingSupport;
  }

  if (candidate.groundingMetadata && candidate.groundingMetadata.supportChunks) {
    result.supportChunks = candidate.groundingMetadata.supportChunks;
  }
  return result;
};

const iteratorToStream = (iterator: AsyncIterator<string>) => {
  return new ReadableStream({
    async pull(controller) {
      const { value, done } = await iterator.next();
      if (done) {
        controller.close();
      } else {
        controller.enqueue(value);
      }
    },
  });
};

async function* processApiResponse(response: Response) {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const readerOutput = await reader.read();
    if (!readerOutput || readerOutput.done) break;
    if (!readerOutput.value) break;

    buffer += decoder.decode(readerOutput.value, { stream: true });

    let bracketCount = 0;
    let jsonStartIndex = buffer.indexOf('{');

    while (jsonStartIndex !== -1) {
      let jsonEndIndex = jsonStartIndex;

      for (let i = jsonStartIndex; i < buffer.length; i++) {
        if (buffer[i] === '{') bracketCount++;
        if (buffer[i] === '}') bracketCount--;

        if (bracketCount === 0) {
          jsonEndIndex = i + 1;
          break;
        }
      }

      if (bracketCount === 0) {
        const jsonString = buffer.slice(jsonStartIndex, jsonEndIndex);
        buffer = buffer.slice(jsonEndIndex);

        try {
          const jsonObject = JSON.parse(jsonString);
          if (jsonObject.candidates && jsonObject.candidates[0]) {
            const candidate = jsonObject.candidates[0];
            const result = responseCandidateToResult(candidate);
            if (Object.keys(result).length > 0) {
              yield JSON.stringify(result) + '\n';
            }
          }
        } catch (error) {
          console.error('Error parsing JSON:', error);
        }

        jsonStartIndex = buffer.indexOf('{');
      } else {
        break;
      }
    }
  }

  if (buffer.trim()) {
    const trimmedBuffer = buffer.trim();
    if (trimmedBuffer !== ']' && trimmedBuffer !== '}') {
      try {
        const jsonObject = JSON.parse(trimmedBuffer);
        if (jsonObject.candidates && jsonObject.candidates[0]) {
          const candidate = jsonObject.candidates[0];
          const result = responseCandidateToResult(candidate);
          if (Object.keys(result).length > 0) {
            yield JSON.stringify(result) + '\n';
          }
        }
      } catch (error) {
        console.error(
          'Error parsing JSON in remaining buffer:',
          error,
          'Buffer:',
          trimmedBuffer,
        );
      }
    }
  }
}

export interface OptionsGroundedGenerationContent {
  role: string;
  parts: { text: string }[];
}

export interface OptionsGroundedGenerationRequest {
  systemInstruction: {
    parts: { text: string };
  };
  contents: OptionsGroundedGenerationContent[];
  model?: string;
  googleGrounding?: boolean;
  vertexGrounding?: boolean;
  vertexConfigId?: string;
}

export interface GroundedGenerationRequestBody {
  systemInstruction: {
    parts: { text: string };
  };
  contents: OptionsGroundedGenerationContent[];
  groundingSpec: {
    groundingSources: {
      googleSearchSource?: {};
      searchSource?: {
        servingConfig: string;
      };
    }[];
  };
  generationSpec: {
    modelId: string;
    temperature: number;
    topP: number;
    topK: number;
  };
}

const mapOptionsToGroundedGenerationRequest = ({
  systemInstruction,
  contents,
  model,
  googleGrounding,
  vertexGrounding,
  vertexConfigId,
}: OptionsGroundedGenerationRequest) => {
  const requestBody: GroundedGenerationRequestBody = {
    systemInstruction,
    contents,
    groundingSpec: {
      groundingSources: [],
    },
    generationSpec: {
      modelId: model || 'gemini-1.5-flash',
      temperature: 0.9,
      topP: 1,
      topK: 1,
    },
  };

  if (googleGrounding) {
    requestBody.groundingSpec.groundingSources.push({
      googleSearchSource: {},
    });
  }

  if (vertexGrounding && vertexConfigId) {
    requestBody.groundingSpec.groundingSources.push({
      searchSource: {
        servingConfig: vertexConfigId,
      },
    });
  }

  if (requestBody.generationSpec.modelId === 'gemini-1.5-flash-high-fidelity') {
    console.log('⚠️ swap model back to gemini-1.5-flash, until allowlisted ⚠️');
    requestBody.generationSpec.modelId = 'gemini-1.5-flash';
  }

  return requestBody;
};

export {
  responseCandidateToResult,
  iteratorToStream,
  processApiResponse,
  mapOptionsToGroundedGenerationRequest,
};
