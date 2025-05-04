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

import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {Observable, catchError, map, throwError} from 'rxjs';
import {Model} from './intent.service';

const allModels = `${environment.backendURL}/models`;

@Injectable({
  providedIn: 'root',
})
export class ModelsService {
  constructor(private http: HttpClient) {}

  getAll(): Observable<Model[]> {
    return this.http.get(allModels).pipe(
      map(response => {
        return response as Model[];
      }),
      catchError(this.handleError)
    );
  }

  protected handleError(error: Response) {
    if (error.status === 404) {
      return throwError(() => new Error());
    } else if (error.status === 400) {
      return throwError(() => error);
    }
    return throwError(() => error);
  }
}
