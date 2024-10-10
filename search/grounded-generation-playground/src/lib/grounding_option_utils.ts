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

import { grounding_options } from './grounding_options';

export interface ExampleQuestion {
  text: string;
  icon?: string;
}

const makeVAISServingConfigPath = (config: {
  project_id?: string;
  app_id?: string;
  location?: string;
}) => {
  const project_id = config.project_id || 'ERR_MISSING_PROJECT_ID';
  const app_id = config.app_id || 'ERR_MISSING_APP_ID';
  const location = config.location || 'global';
  return `projects/${project_id}/locations/${location}/collections/default_collection/engines/${app_id}/servingConfigs/default_search`;
};

export const getConfigByKey = (groundingKey: keyof typeof grounding_options) => {
  return grounding_options[groundingKey];
};

export const makeGroundingSearchSource = (vertexConfigId: string) => {
  return { servingConfig: vertexConfigId };
};

const exampleQuestionsDefault: ExampleQuestion[] = [
  { text: 'When is the next total solar eclipse in US?', icon: 'eclipse' },
  {
    text: "How many qubits does the world's largest quantum computer have?",
    icon: 'cpu',
  },
  {
    text: 'Who was the CEO of YouTube when Google acquired it?',
    icon: 'youtube',
  },
];

export const makeExampleQuestions = (): ExampleQuestion[] => {
  return exampleQuestionsDefault.slice(0, 3);
};
