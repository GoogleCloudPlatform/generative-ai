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
import {environment} from 'src/environments/environment';

// const audioChatUrl = `http://localhost:8080/api/audio_chat`;
const audioChatUrl = `${environment.backendURL}/audio_chat`;

@Injectable({
  providedIn: 'root',
})
export class SpeechToTextService {
  constructor(private http: HttpClient) {}

  async transcribeAudio(audioBlob: Blob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'audio.wav');
    return this.http.post(audioChatUrl, formData);
  }
}
