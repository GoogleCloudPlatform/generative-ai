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

/**
 * Ungrounded generation for side by side generation
 *
 *
 */
import { NextRequest, NextResponse } from 'next/server';
import { VertexAI } from '@google-cloud/vertexai';

const PROJECT_ID = process.env.PROJECT_ID;
const LOCATION = process.env.LOCATION;
const MODEL = 'gemini-1.5-flash-001';

export async function POST(req: NextRequest) {
  const { query, model, googleGrounding, vertexGrounding } = await req.json();

  const vertexAI = new VertexAI({ project: PROJECT_ID, location: LOCATION });
  const generativeModel = vertexAI.getGenerativeModel({ model: MODEL });

  const request = {
    contents: [
      {
        role: 'user',
        parts: [{ text: query }],
      },
    ],
    generationConfig: {
      maxOutputTokens: 2048,
      temperature: 0.9,
      topP: 1,
      topK: 1,
    },
  };

  const stream = new ReadableStream({
    async start(controller) {
      console.log('Received POST request to /api/ungrounded');
      const result = await generativeModel.generateContentStream(request);
      for await (const item of result.stream) {
        const chunk = item.candidates?.[0]?.content?.parts?.[0]?.text ?? '';
        controller.enqueue(new TextEncoder().encode(chunk));
      }
      controller.close();
    },
  });

  return new NextResponse(stream);
}
