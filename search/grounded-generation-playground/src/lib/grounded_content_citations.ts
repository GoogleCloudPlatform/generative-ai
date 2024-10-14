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

import { StringToBoolean } from 'class-variance-authority/types';

interface GroundedContent {
  content: string;
  groundingSupport?: GroundingSupport[];
  supportChunks?: SupportChunk[];
  searchEntryPoint?: string;
  truncateAfter: number;
}

interface GroundingSupport {
  supportChunkIndices: number[];
  claimText: string;
}

interface SupportChunkMetadata {
  uri?: string;
  domain?: string;
  title?: string;
  index?: number;
  source?: string;
}

interface SupportChunk {
  index: number;
  sourceMetadata?: SupportChunkMetadata;
  chunkText?: string;
}

interface TransformedCitation {
  chunkIndex: number;
  uri: string;
  title: string;
  text: string;
  source: string;
  index?: number;
}

interface TransformedContent {
  citedContent: string;
  citations: TransformedCitation[];
}

/**
 * Transforms the output from the Grounded Generation API into a format that allows for inline citations.
 *
 * This function takes the original content, grounding support information, support chunks, and search entry point
 * as input. It processes the grounding support information to insert citations into the original content and
 * prepares a list of citations with their corresponding metadata.
 *
 * @param {GroundedContent} groundedContent - The content and metadata returned from the Grounded Generation API.
 * @returns {TransformedContent} - An object containing the content with citations inserted and a list of citations.
 */
export function transformGroundedContent({
  content,
  groundingSupport,
  supportChunks = [],
  searchEntryPoint,
  truncateAfter,
}: GroundedContent): TransformedContent {
  let citedContent = content;
  const usedSources = new Set<string>();
  const citations: TransformedCitation[] = [];

  // Support chunks are provided by index, make a convenient lookup map.
  const supportChunksByIndex = new Map<number, SupportChunk>();
  supportChunks.forEach((supportChunk, i) => {
    const index = supportChunk.index || i;
    if (
      supportChunksByIndex.has(index) &&
      supportChunksByIndex.get(index) !== supportChunk
    ) {
      console.error(
        `Clobbered supportChunk at ${index}, new ${JSON.stringify(
          supportChunk,
        )}, old ${JSON.stringify(supportChunksByIndex.get(index))}`,
      );
    }
    supportChunksByIndex.set(index, supportChunk);
  });

  if (groundingSupport) {
    groundingSupport.forEach((support, supportIndex) => {
      const citation = support.supportChunkIndices.map((i) => `[${i + 1}] `).join('');
      citedContent = citedContent.replace(
        support.claimText,
        `${support.claimText} ${citation}`,
      );
      support.supportChunkIndices.forEach((chunkIndex) => {
        const chunk = supportChunksByIndex.get(chunkIndex) || supportChunks[chunkIndex];
        if (!chunk) return;

        const sourceMetadata = chunk.sourceMetadata || {};
        const uri = sourceMetadata.uri || '';
        const title = sourceMetadata.title || sourceMetadata.domain || '';
        const index = sourceMetadata.index ?? chunkIndex;
        let source = sourceMetadata.source;
        const text = chunk.chunkText
          ? chunk.chunkText.substring(0, truncateAfter || 1500)
          : 'No text available';

        if (uri.length === 0) return;
        if (usedSources.has(uri)) return;
        usedSources.add(uri);

        if (
          uri.substring(0, 63) ==
          'https://vertexaisearch.cloud.google.com/grounding-api-redirect/'
        ) {
          source = 'Google Search';
        }

        citations.push({
          chunkIndex,
          uri,
          title,
          text,
          source: source || '',
          index,
        });
      });
    });
  }

  return {
    citedContent,
    citations,
  };
}
