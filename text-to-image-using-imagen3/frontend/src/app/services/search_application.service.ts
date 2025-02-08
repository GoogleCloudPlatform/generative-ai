import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';
import { map } from 'rxjs/operators';
import {Observable} from 'rxjs';
import { SearchApplication } from '../models/search_application.model';

const configURL = `${environment.backendURL}/search/application`;

@Injectable({
  providedIn: 'root'
})
export class SearchApplicationService {

  constructor(private readonly http: HttpClient) { }

  get(): Observable<SearchApplication>{
      return this.http.get(configURL).pipe(map(response=> response as SearchApplication));
  }

  create(searchApplication: SearchApplication){
    return this.http.post(configURL, searchApplication);
  }

  update(engine_id:string, searchApplication: SearchApplication){
    return this.http.put(`${configURL}/${engine_id}`, searchApplication);
  }
}
