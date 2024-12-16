import { map, Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Engine } from '../models/engine.model';
import { environment } from 'src/environments/environment';

const ENGINES_URL = `${environment.backendURL}/search/engines`;

@Injectable({
  providedIn: 'root'
})
export class EnginesService {

  constructor(private http: HttpClient) {}

  getAll(): Observable<Engine[]> {
    return this.http.get(ENGINES_URL).pipe(map(response => response as Engine[]))
  }
}
