import {HttpClient} from '@angular/common/http';
import {Injectable} from '@angular/core';
import {environment} from 'src/environments/environment';
import {map} from 'rxjs/operators';
import {SearchRequest} from '../models/search.model';
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

    if (!userImage) {
      // Redirect to homepage and alert that you need to upload an image first
      this.router.navigate(['/']);
      alert('Please upload an image first.');
      return throwError(
        () => new Error('No image and no search term provided.')
      );
    }

    const formData = new FormData();
    formData.append('term', searchRequest.term);
    formData.append('generationModel', searchRequest.model);
    formData.append('numberOfImages', searchRequest.numberOfResults.toString());
    formData.append(
      'maskDistilation',
      searchRequest.maskDistilation.toString()
    );
    formData.append('userImage', userImage, userImage.name);

    return this.http
      .post(searchURL, formData)
      .pipe(map(response => response as GeneratedImage[]));
  }
}
