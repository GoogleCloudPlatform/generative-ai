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

interface ExampleQuestion {
  text: string;
  icon?: string;
}

interface GroundingOption {
  data: string;
  retriever: string;
  subtext: string;
  description: string;
  type: string;
  project_id?: string;
  app_id?: string;
  data_store_id?: string;
  servingConfig?: string;
  icon: string;
  hidden?: boolean;
  exampleQuestions?: ExampleQuestion[];
}

const grounding_options: Record<string, GroundingOption> = {};

export { grounding_options };
