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

  postChat(query: string, chat_id?: string | null): Observable<Chat> {
    query = query.replace(/\s+/g, " ").trim();
    const body: CreateChatRequest = {
      text: query,
    };
    if (chat_id) {
      body.chat_id = chat_id;
    }
    return this.http.post<Chat>(chatsUrl, body);
  }
}
