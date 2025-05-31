/**
 * Copyright 2025 Google LLC
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

import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {HttpClient} from '@angular/common/http';

const intentURL = `${environment.backendURL}/questions/intents`;
const manageIntentURL = `${environment.backendURL}/intents`;

export type Intent = {
  id?: string;
  question: string;
  intent: string;
  author: string;
  timestamp?: string;
};

export interface IntentDetails {
  name: string;
  gcp_bucket?: string;
  ai_model: string;
  ai_temperature: string;
  prompt: string;
  status: string;
  questions: string[];
}

export interface Model {
  name: string;
  models: string;
}

export type GetChunksRequest = {
  question: string;
  intent?: string;
};

export interface IntentChunk {
  intent?: string;
  suggested_question?: string[];
  information_chunks?: Chunk[];
}

export interface Chunk {
  id?: string;
  distance?: string;
  content?: string;
}

@Injectable({
  providedIn: 'root',
})
export class IntentService {
  constructor(private http: HttpClient) {}

  getAllQuestion() {
    return this.http.get<Intent[]>(intentURL);
  }

  addQuestion(intent: Intent) {
    return this.http.post(intentURL, intent);
  }

  deleteQuestion(question_id: string) {
    return this.http.delete(`${intentURL}/${question_id}`);
  }

  getIntentChunks(reqObj: GetChunksRequest) {
    return this.http.post<IntentChunk>(`${intentURL}/get_chunks`, reqObj);
  }

  saveIntent(reqObj: IntentDetails) {
    return this.http.post<IntentDetails>(manageIntentURL, reqObj);
  }

  updateIntent(reqObj: IntentDetails) {
    return this.http.put<IntentDetails>(
      `${manageIntentURL}/${reqObj.name}`,
      reqObj
    );
  }

  getAllIntent() {
    return this.http.get<Array<IntentDetails>>(manageIntentURL);
  }

  deleteIntent(name: string) {
    return this.http.delete<IntentDetails>(`${manageIntentURL}/${name}`);
  }
}
