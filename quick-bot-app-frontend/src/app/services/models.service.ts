import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { Observable, catchError, map, throwError } from 'rxjs';
import { Model } from './intent.service';

const allModels = `${environment.backendURL}/models`;

@Injectable({
  providedIn: 'root'
})
export class ModelsService {

  constructor(private http: HttpClient) {}

  getAll(): Observable<Model[]> {
    return this.http.get(allModels).pipe(
      map(response => {
        return response as Model[];
      }),
      catchError(this.handleError));
  }

  protected handleError(error: Response) {
    if (error.status === 404) {
      return throwError(() => new Error())
    } else if (error.status === 400) {
      return throwError(() => error)
    }
    return throwError(() => error);
  }
}
