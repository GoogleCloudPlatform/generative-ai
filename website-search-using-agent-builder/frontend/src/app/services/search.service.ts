import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {map} from 'rxjs/operators';
import {SearchRequest, SearchResponse} from '../models/search.model';

const searchURL = `${environment.backendURL}/search`;

@Injectable({
  providedIn: 'root',
})
export class SearchService {
  constructor(private http: HttpClient) {}

  search(term: string) {
    const request: SearchRequest = {term: term};
    return this.http
      .post(searchURL, request)
      .pipe(map(response => response as SearchResponse));
  }
}
