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

"use strict";
import { GoogleAuth } from "google-auth-library";
import { dotprompt } from "@genkit-ai/dotprompt";
import { vertexAI } from "@genkit-ai/vertexai";
import { ollama } from "genkitx-ollama";
import { ConfigOptions } from "@genkit-ai/core";
import { googleCloud } from "@genkit-ai/google-cloud";
import { AlwaysOnSampler } from "@opentelemetry/sdk-trace-base";

let auth: GoogleAuth;

function getAuthClient() {
  // Lazy load GoogleAuth client.
  if (!auth) {
    auth = new GoogleAuth();
  }
  return auth;
}

export async function getIdToken(url: string): Promise<string> {
  const auth = getAuthClient();
  const client = await auth.getIdTokenClient(url);
  return client.idTokenProvider.fetchIdToken(url);
}

export const genkitConfig = {
  plugins: [
    vertexAI({ location: "europe-west2" }),
    dotprompt(),
    googleCloud({
      telemetryConfig: {
        forceDevExport: true, // Set this to true to export telemetry for local runs
        sampler: new AlwaysOnSampler(),
        autoInstrumentation: true,
        autoInstrumentationConfig: {
          "@opentelemetry/instrumentation-fs": { enabled: false },
          "@opentelemetry/instrumentation-dns": { enabled: true },
          "@opentelemetry/instrumentation-net": { enabled: true },
        },
      },
    }),
    ollama({
      models: [{ name: process.env.OLLAMA_MODEL_NAME || "gemma2:9b" }],
      serverAddress:
        process.env.OLLAMA_SERVER_ADDRESS || "http://127.0.0.1:8080",
      requestHeaders: async (params) => ({
        Authorization: `Bearer ${await getIdToken(params.serverAddress)}`,
      }),
    }),
  ],
  // Log debug output to the console.
  logLevel: "debug",
  enableTracingAndMetrics: true,
  telemetry: {
    instrumentation: "googleCloud",
    logger: "googleCloud",
  },
} as ConfigOptions;
