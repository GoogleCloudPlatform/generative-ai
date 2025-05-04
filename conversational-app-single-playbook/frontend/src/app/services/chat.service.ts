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
import {HttpClient} from '@angular/common/http';
import {Observable} from 'rxjs';
import {Chat, CreateChatRequest} from '../models/chat.model';
import {environment} from 'src/environments/environment';

const chatsUrl = `${environment.backendURL}/chats`;

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  constructor(private http: HttpClient) {}

  postChat(query: string): Observable<Chat> {
    query = query.replace(/\s+/g, ' ').trim();
    const body: CreateChatRequest = {
      text: query,
    };
    return this.http.post<Chat>(chatsUrl, body);
  }
}
