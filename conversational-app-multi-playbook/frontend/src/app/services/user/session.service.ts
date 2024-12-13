import { Injectable } from '@angular/core';
import { v4 as uuid } from 'uuid'; 

const SESSION_KEY = "pasid"

@Injectable({
  providedIn: 'root'
})
export class SessionService {

  constructor() { }

  getSession(): string | null {
    return sessionStorage.getItem(SESSION_KEY);
  }

  createSession() {
    sessionStorage.setItem(SESSION_KEY, uuid())
  }
}