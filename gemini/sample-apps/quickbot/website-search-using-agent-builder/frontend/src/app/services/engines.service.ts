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

import {map, Observable} from 'rxjs';
import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {Engine} from '../models/engine.model';
import {environment} from 'src/environments/environment';

const ENGINES_URL = `${environment.backendURL}/search/engines`;

@Injectable({
  providedIn: 'root',
})
export class EnginesService {
  constructor(private http: HttpClient) {}

  getAll(): Observable<Engine[]> {
    return this.http
      .get(ENGINES_URL)
      .pipe(map(response => response as Engine[]));
  }
}
