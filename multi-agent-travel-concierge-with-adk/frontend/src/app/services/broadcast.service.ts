import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { Message } from '../models/messegeType.model';

@Injectable({
  providedIn: 'root'
})
export class BroadcastService {
  initialChatQuery = '';
  chatQuery$: BehaviorSubject<Message>;

  constructor() {
    this.chatQuery$  = new BehaviorSubject<Message>({'type': 'bot', 'contentParts': [{'text':'Ask me anything ?','type':'text'}], shareable: false,});
  }

  nextChatQuery(chatQuery: Message) {
    this.chatQuery$.next(chatQuery);
  }
}
