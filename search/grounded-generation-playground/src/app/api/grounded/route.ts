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
 * Grounded generation for side by side
 *
 */
import { NextRequest, NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import {
  responseCandidateToResult,
  iteratorToStream,
  processApiResponse,
  mapOptionsToGroundedGenerationRequest,
} from '@/lib/apiutils';

const PROJECT_NUMBER = process.env.PROJECT_NUMBER;
const API_ENDPOINT = `https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/global:streamGenerateGroundedContent`;

export async function POST(req: NextRequest) {
  console.log('Received POST request to /api/grounded');

  const { query, model, googleGrounding, vertexGrounding, vertexConfigId, temperature } =
    await req.json();
  if (!query || query.length === 0) {
    throw new Error('No query provided');
  }
  console.log('Request body:', {
    query,
    model,
    googleGrounding,
    vertexGrounding,
    vertexConfigId,
  });

  // Use Google Auth Library to get the access token
  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform'],
  });
  const client = await auth.getClient();
  const accessToken = await client.getAccessToken();

  if (!accessToken.token) {
    throw new Error('Failed to obtain access token');
  }
  // Single turn content, just a user query.
  const contents = [
    {
      role: 'user',
      parts: [{ text: query }],
    },
  ];
  const systemInstruction = {
    parts: {
      text: 'You are a helpful AI assistant using grounding sources.',
    },
  };
  const requestBody = mapOptionsToGroundedGenerationRequest({
    systemInstruction,
    contents,
    model,
    googleGrounding,
    vertexGrounding,
    vertexConfigId,
  });

  console.log('Sending request to Discovery Engine API');
  console.log('Request body:', JSON.stringify([requestBody]));

  try {
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify([requestBody]),
    });

    console.log('Received response from Discovery Engine API');
    console.log('Response status:', response.status);
    console.log('Response headers:', response.headers);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response from API:', errorText);
      throw new Error(`API request failed with status ${response.status}: ${errorText}`);
    }

    const iterator = processApiResponse(response);
    const stream = iteratorToStream(iterator);

    return new NextResponse(stream, {
      headers: {
        'Content-Type': 'text/plain',
        'Transfer-Encoding': 'chunked',
        'Cache-Control': 'no-cache, no-transform',
        'X-Accel-Buffering': 'no',
      },
    });
  } catch (error) {
    console.error('Error in POST handler:', error);
    return new NextResponse(JSON.stringify({ error: 'Internal Server Error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
