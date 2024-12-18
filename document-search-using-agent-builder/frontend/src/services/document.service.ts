import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class DocumentService {

  constructor(private http: HttpClient) { }

  getDocument(url: string): Observable<Blob> {
    const headers = new HttpHeaders({
      'responseType': 'blob' 
    });

    return this.http.get(url, { headers, responseType: 'blob' });
  }

}
