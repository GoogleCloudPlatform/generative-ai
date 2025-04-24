import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Chat, CreateChatRequest } from '../models/chat.model';
import { environment } from 'src/environments/environment';

const chatsUrl = `${environment.backendURL}/chats`;

@Injectable({
  providedIn: 'root'
})
export class ChatService {

  constructor(private http: HttpClient) {}

  postChat(query: string): Observable<Chat> {
    query = query.replace(/\s+/g, " ").trim();
    const body: CreateChatRequest = {
      text: query,
    };
    return this.http.post<Chat>(chatsUrl, body);
  }
}
