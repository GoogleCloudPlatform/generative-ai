import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { Message } from '../models/messegeType.model';

@Injectable({
  providedIn: 'root'
})
export class BroadcastService {
  initialChatQuery = '';
  chatQuery$: BehaviorSubject<string>;
  
  constructor() { 
    this.chatQuery$  = new BehaviorSubject<string>('');
  }

  nextChatQuery(chatQuery: string) {
    this.chatQuery$.next(chatQuery);
  }
}
