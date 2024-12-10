import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { result, CreateChatRequest } from '../models/chat.model';
import { environment } from 'src/environments/environment';

const chatsUrl = `${environment.backendURL}/searches`;

@Injectable({
  providedIn: 'root'
})
export class ChatService {

  constructor(private http: HttpClient) {}

  postChat(query: string): Observable<result> {
    query = query.replace(/\s+/g, " ").trim();
    const body: CreateChatRequest = {
      search: query,
    };
    return this.http.post<result>(chatsUrl, body);
  }
}
