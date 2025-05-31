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
import {map} from 'rxjs/operators';
import {Observable} from 'rxjs';
import {SearchApplication} from '../models/search_application.model';

const configURL = `${environment.backendURL}/search/application`;

@Injectable({
  providedIn: 'root',
})
export class SearchApplicationService {
  constructor(private readonly http: HttpClient) {}

  get(): Observable<SearchApplication> {
    return this.http
      .get(configURL)
      .pipe(map(response => response as SearchApplication));
  }

  create(searchApplication: SearchApplication) {
    return this.http.post(configURL, searchApplication);
  }

  update(engine_id: string, searchApplication: SearchApplication) {
    return this.http.put(`${configURL}/${engine_id}`, searchApplication);
  }
}
