import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {map} from 'rxjs/operators';
import {SearchRequest} from '../models/search.model';
import {GeneratedImage} from '../models/generated-image.model';

const searchURL = `${environment.backendURL}/search`;

@Injectable({
  providedIn: 'root',
})
export class SearchService {
  constructor(private http: HttpClient) {}

  search(searchRequest: SearchRequest) {
    return this.http
      .post(searchURL, searchRequest)
      .pipe(map(response => response as GeneratedImage[]));
  }
}
