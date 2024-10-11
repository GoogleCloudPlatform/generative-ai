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

import React from 'react';
import Icon from '@/components/ui/icons';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import {
  mapOptionsToGroundedGenerationRequest,
  GroundedGenerationRequestBody,
} from '@/lib/apiutils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AboutPageContentProps {
  selectedModel: string;
  googleGrounding: boolean;
  vertexGrounding: boolean;
  vertexConfigId: string;
  temperature: number;
  activeAboutTab: string;
  setActiveAboutTab: (tab: string) => void;
}

// Use the GroundedGenerationRequestBody type directly
type RequestObject = GroundedGenerationRequestBody;

const AboutPageContent: React.FC<AboutPageContentProps> = ({
  selectedModel,
  googleGrounding,
  vertexGrounding,
  vertexConfigId,
  temperature,
  activeAboutTab,
  setActiveAboutTab,
}) => {
  const requestObj: RequestObject = mapOptionsToGroundedGenerationRequest({
    systemInstruction: { parts: { text: 'Your system instruction here' } },
    contents: [{ role: 'user', parts: [{ text: 'Your query here' }] }],
    model: selectedModel,
    googleGrounding,
    vertexGrounding,
    vertexConfigId,
  });

  return (
    <Tabs value={activeAboutTab} onValueChange={setActiveAboutTab} className="w-full">
      <TabsList className="grid w-full grid-cols-4 mb-6 bg-zinc-800">
        <TabsTrigger
          value="javascript"
          className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
        >
          JavaScript
        </TabsTrigger>
        <TabsTrigger
          value="python"
          className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
        >
          Python
        </TabsTrigger>
        <TabsTrigger
          value="curl"
          className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
        >
          Curl Command
        </TabsTrigger>
        <TabsTrigger
          value="notes"
          className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
        >
          Notes
        </TabsTrigger>
      </TabsList>
      <TabsContent value="javascript">
        <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
          {makeJs(requestObj)}
        </pre>
      </TabsContent>
      <TabsContent value="python">
        <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
          {makePython(requestObj)}
        </pre>
      </TabsContent>
      <TabsContent value="curl">
        <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
          {makeCurl(requestObj)}
        </pre>
      </TabsContent>
      <TabsContent value="notes">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {googleGrounding && (
            <Card className="rounded-2xl bg-zinc-800 text-white h-full">
              <CardContent>
                <h3 className="my-2 flex items-center">
                  <Icon type="google" className="mr-2 text-gray-400 h-6 w-6" />
                  Google Search
                </h3>
                <strong className="text-zinc-200 text-sm">
                  <p>Ground with Google Search.</p>
                </strong>
                <div className="text-zinc-400 text-sm">
                  <p>Search results provided by Google Search.</p>
                  <p>
                    Dynamic Retrieval can be enabled along with a threshold to only do a
                    Google Search when we think it's needed. Fewer searches saves you cost
                    and speeds up the response.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
          {vertexGrounding && (
            <Card className="rounded-2xl bg-zinc-800 text-white h-full">
              <CardContent>
                <h3 className="my-2 flex items-center">
                  <Icon type="vertex" className="mr-2 text-gray-400 h-6 w-6" />
                  Vertex AI Search
                </h3>
                <p>Enter your own Vertex AI Search project path.</p>
                <p>
                  An example would look like:{' '}
                  <code>
                    projects/555555555555/locations/global/collections/default_collection/engines/VERTEX_AI_SEARCH_APP_ID/servingConfigs/default_search
                  </code>
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
};

const makeCurl = (requestObj: RequestObject): string => {
  const PROJECT_NUMBER = process.env.PROJECT_NUMBER;
  const API_ENDPOINT = `https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/global:streamGenerateGroundedContent`;
  const requestStr = JSON.stringify(requestObj);
  return `curl -X POST \\  
-H "Authorization: Bearer $(gcloud auth print-access-token)" \\
-H "Content-Type: application/json" \\
"${API_ENDPOINT}" \\
-d '${requestStr}'`;
};

const makeJs = (requestObj: RequestObject): string => {
  const PROJECT_NUMBER = process.env.PROJECT_NUMBER;
  const API_ENDPOINT = `https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/global:streamGenerateGroundedContent`;
  const requestStr = JSON.stringify(requestObj, null, 4);
  return `
const auth = new GoogleAuth({scopes: ['https://www.googleapis.com/auth/cloud-platform']});
const client = await auth.getClient();
const accessToken = await client.getAccessToken();

const response = await fetch('${API_ENDPOINT}', {
    method: 'POST',
    headers: {
        Authorization: 'Bearer \${accessToken.token}',
        'Content-Type': 'application/json',
    },
    body: JSON.parse(\`[
${requestStr}
]\`), 
});`;
};

// TODO: abhishekbhgwt@: Update to client library when available
const makePython = (requestObj: RequestObject): string => {
  const PROJECT_NUMBER = process.env.PROJECT_NUMBER;
  const API_ENDPOINT = `https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/global:streamGenerateGroundedContent`;
  const requestStr = JSON.stringify(requestObj, null, 4);
  return `import requests
import json
import google.auth
credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])


API_ENDPOINT = "${API_ENDPOINT}"

headers = {
    "Authorization": f"Bearer {credentials.token}",
    "Content-Type": "application/json"
}

data = json.loads(f'''[
${requestStr}
]''')

response = requests.post(API_ENDPOINT, headers=headers, json=data)`;
};

export default AboutPageContent;
