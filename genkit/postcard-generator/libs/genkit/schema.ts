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
import { z } from "zod";

/**
 * Input for Genkit Flow
 */
export const PostcardFlowSchema = z.object({
  start: z.string(),
  end: z.string(),
  stops: z.array(z.string()).optional(),
  keywords: z.string().optional(),
  sender: z.string(),
  recipient: z.string(),
});
export type PostcardFlow = z.infer<typeof PostcardFlowSchema>;

export const PostcardMapLLMRequestSchema = z.object({
  start: z.string(),
  end: z.string(),
  mapImage: z.optional(z.string()),
  sender: z.string(),
  recipient: z.string(),
});

export type PostcardMapLLMRequest = z.infer<typeof PostcardMapLLMRequestSchema>;

export const PostcardMapLLMResponseSchema = z.object({
  description: z.string(),
  story: z.string(),
});

export type PostcardMapLLMResponse = z.infer<
  typeof PostcardMapLLMResponseSchema
>;

export const PostcardMapResult = z.object({
  description: z.string(),
  story: z.string(),
});

export const PostcardImageLLMRequestSchema = z.object({
  start: z.string(),
  end: z.string(),
  story: z.string(),
});

export type PostcardImageLLMRequest = z.infer<
  typeof PostcardImageLLMRequestSchema
>;

export const PostcardResultSchema = z.object({
  description: z.string(),
  image: z.string(),
  map: z.string(),
  story: z.string(),
});

export type PostcardResult = z.infer<typeof PostcardResultSchema>;
