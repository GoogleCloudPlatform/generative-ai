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

'use client';

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { transformGroundedContent } from '@/lib/grounded_content_citations';
import { GroundingSupport, SupportChunk } from '@/app/page';

interface GroundedTextBlockProps {
  role: 'user' | 'model';
  content: string;
  groundingSupport?: GroundingSupport[];
  supportChunks?: SupportChunk[];
  searchEntryPoint?: string;
  truncateAfter?: number;
}

const GroundedTextBlock: React.FC<GroundedTextBlockProps> = ({
  content,
  groundingSupport,
  supportChunks,
  searchEntryPoint,
  truncateAfter = 1500,
}) => {
  if (!content) return null;
  if (
    !groundingSupport ||
    !supportChunks ||
    groundingSupport.length === 0 ||
    supportChunks.length === 0
  ) {
    return <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>;
  }

  // Transform into citedContent and a simple list of citations.
  const { citedContent, citations } = transformGroundedContent({
    content,
    groundingSupport,
    supportChunks,
    truncateAfter,
  });
  const isSourcesShown =
    (searchEntryPoint && searchEntryPoint.length > 0) ||
    (citedContent && citations && citations.length > 0);

  return (
    <div className="cited-text">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{citedContent}</ReactMarkdown>
      {isSourcesShown && (
        <h3 className="text-sm font-semibold mt-2 mb-0 text-zinc-500">Sources:</h3>
      )}
      {searchEntryPoint && searchEntryPoint.length > 0 && (
        <div className="mt-2 rounded">
          <div dangerouslySetInnerHTML={{ __html: searchEntryPoint }} />
        </div>
      )}
      {citedContent && citations && citations.length > 0 && (
        <div className="mt-2">
          {citations.map(({ chunkIndex, uri, title, text, source }, index) => (
            <TooltipProvider key={index}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Card className="bg-zinc-800 border-zinc-700 hover:bg-zinc-700 transition-colors duration-200">
                    <CardContent className="flex items-center p-2 pl-3 cursor-pointer">
                      {source == 'Google Search' ? (
                        <span className="text-xs prose prose-invert truncate">
                          [{chunkIndex + 1}]{' '}
                          <a href={uri} target="_blank" rel="noopener noreferrer">
                            {title}
                          </a>
                        </span>
                      ) : (
                        <span className="text-xs prose prose-invert truncate">
                          [{chunkIndex + 1}] {title} <br />
                          <small>{niceUri(uri)}</small>
                        </span>
                      )}
                    </CardContent>
                  </Card>
                </TooltipTrigger>
                <TooltipContent className="max-w-4/5 max-w-600px">
                  <p className="text-sm text-gray-300 truncate">{title}</p>
                  <p className="text-xs prose prose-invert">
                    {text ? text.substring(0, truncateAfter) : ''}
                    ...
                  </p>
                  <p className="text-xs mt-2 prose prose-invert">
                    Source: {niceUri(uri)}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ))}
        </div>
      )}
    </div>
  );
};

const niceUri = (uri: string) => {
  if (!uri) return '';
  return uri;
};

export default GroundedTextBlock;
