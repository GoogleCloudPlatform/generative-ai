import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {map} from 'rxjs/operators';
import {SearchRequest, SearchResponse} from '../models/search.model';
import {GeneratedImage} from '../models/generated-image.model';
import {ImageService} from './image/image.service';
import {Router} from '@angular/router';
import {Observable, throwError} from 'rxjs';

const searchURL = `${environment.backendURL}/search`;

@Injectable({
  providedIn: 'root',
})
export class SearchService {
  constructor(
    private http: HttpClient,
    private imageService: ImageService,
    private router: Router
  ) {}

  search(searchRequest: SearchRequest): Observable<GeneratedImage[]> {
    const userImage = this.imageService.getImage();

    if (!userImage && searchRequest.term === '') {
      // Redirect to homepage and alert that you need to upload an image first
      this.router.navigate(['/']);
      alert('Please upload an image first.');
      return throwError(
        () => new Error('No image and no search term provided.')
      );
    }

    const formData = new FormData();
    if (userImage) formData.append('userImage', userImage, userImage.name);

    formData.append('term', searchRequest.term);
    formData.append('model', searchRequest.model);
    formData.append('aspectRatio', searchRequest.aspectRatio);

    return this.http
      .post(searchURL, formData)
      .pipe(map(response => response as GeneratedImage[]));
  }
}
