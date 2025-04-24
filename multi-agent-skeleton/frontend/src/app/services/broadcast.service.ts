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
    this.chatQuery$  = new BehaviorSubject<Message>({'body':'Ask me anything ?','type':'bot', shareable: false,});
  }

  nextChatQuery(chatQuery: Message) {
    this.chatQuery$.next(chatQuery);
  }
}
