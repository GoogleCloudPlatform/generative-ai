/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Injectable, OnDestroy } from '@angular/core';
import { Subject, Observable, BehaviorSubject, Subscription } from 'rxjs';
import { environment } from 'src/environments/environment';

// Define a type for messages from the server for better type safety
export interface ServerMessage {
  operation?: 'start' | 'end_of_turn' | 'fatal_error' | 'error_and_close';
  answer?: any;
  intent?: string;
  suggested_questions?: any[];
  error?: string;
  [key: string]: any;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'reconnecting' | 'closed_by_server' | 'closed_by_client' | 'aborted' | 'processing_complete';

/**
 * Helper function to convert HTTP/HTTPS URL to WS/WSS URL.
 */
function getWebSocketUrl(httpUrl: string | undefined): string {
  const defaultWsUrl = "ws://localhost:8000/api/chats";
  if (!httpUrl) {
    console.warn("environment.backendURL is not defined, falling back to default WebSocket URL:", defaultWsUrl);
    return defaultWsUrl;
  }

  let wsUrl = httpUrl;
  if (httpUrl.startsWith('https://')) {
    wsUrl = 'wss://' + httpUrl.substring('https://'.length);
  } else if (httpUrl.startsWith('http://')) {
    wsUrl = 'ws://' + httpUrl.substring('http://'.length);
  } else {
    console.warn(`backendURL "${httpUrl}" does not have a standard http/https protocol prefix. Assuming ws:// and appending /chats`);
    wsUrl = 'ws://' + httpUrl;
  }

  const chatsApiPath = "/chats";
  if (wsUrl.endsWith('/')) {
    wsUrl = wsUrl.slice(0, -1);
  }
  if (!wsUrl.endsWith(chatsApiPath)) {
    if (wsUrl.includes('/api/') && !wsUrl.endsWith('/chats')) {
      wsUrl = wsUrl + (wsUrl.endsWith('/') ? 'chats' : 'chats');
    } else if (!wsUrl.includes('/api/')) {
      wsUrl = wsUrl + chatsApiPath;
    }
  }
  console.log("Constructed WebSocket URL:", wsUrl);
  return wsUrl;
}


@Injectable({
  providedIn: 'root'
})
export class ChatService implements OnDestroy {
  private BASE_SOCKET_URL = getWebSocketUrl(environment.backendURL);
  private websocket: WebSocket | null = null;
  private serviceSubscriptions: Subscription = new Subscription();

  private messageSubject = new Subject<ServerMessage>();
  private connectionStatusSubject = new BehaviorSubject<ConnectionStatus>('disconnected');

  constructor() {
    console.log("ChatService (WebSocket) instantiated with URL:", this.BASE_SOCKET_URL);
    // Optionally, you could call connect() here if the service should always
    // try to connect upon instantiation. Or, let the consuming component call it.
    // this.connect();
  }

  public getMessages(): Observable<ServerMessage> {
    return this.messageSubject.asObservable();
  }

  public getConnectionStatus(): Observable<ConnectionStatus> {
    return this.connectionStatusSubject.asObservable();
  }

  /**
   * Establishes a WebSocket connection if not already connected or connecting.
   */
  public connect(): void {
    if (this.websocket && (this.websocket.readyState === WebSocket.OPEN || this.websocket.readyState === WebSocket.CONNECTING)) {
      console.warn("connect() called while WebSocket is already open or connecting.");
      return;
    }

    this.connectionStatusSubject.next('connecting');
    const socketUrl = this.BASE_SOCKET_URL;
    console.log("Attempting to connect to WebSocket at:", socketUrl);

    try {
      this.websocket = new WebSocket(socketUrl);
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this.connectionStatusSubject.next('error');
      this.messageSubject.error(error);
      return;
    }

    this.websocket.onopen = (event) => {
      console.log("WebSocket connection established:", event);
      this.connectionStatusSubject.next('connected');
      // No initial message sent automatically on open anymore.
      // The backend will send {"operation": "start"} after creating a session.
    };

    this.websocket.onmessage = (event) => {
      try {
        const serverMessage: ServerMessage = JSON.parse(event.data as string);
        console.log("Message from server: ", serverMessage);
        this.messageSubject.next(serverMessage);

        if (serverMessage.operation === "end_of_turn") {
          console.log("Server indicated end of turn.");
          this.connectionStatusSubject.next('processing_complete');
        } else if (serverMessage.operation === "start") {
          console.log("Server indicated session start.");
          // 'connected' status is already set by onopen.
          // If 'start' implies the bot is immediately ready for input after connection,
          // you could also set to 'processing_complete' here, or a new 'ready' status.
          // For now, 'connected' means the channel is open.
        } else if (serverMessage.operation === "fatal_error" || serverMessage.operation === "error_and_close") {
          console.error("Server indicated a fatal error or an error requiring close:", serverMessage.error);
          this.connectionStatusSubject.next('error');
        }
      } catch (e) {
        console.error("Error parsing JSON message from server or received non-JSON message:", event.data, e);
        this.messageSubject.error(new Error(`Failed to parse server message: ${event.data}`));
        this.connectionStatusSubject.next('error');
      }
    };

    this.websocket.onerror = (event) => {
      console.error("WebSocket error observed:", event);
      this.connectionStatusSubject.next('error');
      this.messageSubject.error(event);
    };

    this.websocket.onclose = (event) => {
      console.log("WebSocket connection closed:", event);
      const currentStatus = this.connectionStatusSubject.value;
      if (event.wasClean) {
        console.log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        if (currentStatus !== 'closed_by_server' && currentStatus !== 'closed_by_client' && currentStatus !== 'aborted') {
          this.connectionStatusSubject.next('disconnected');
        }
      } else {
        console.error('Connection died unexpectedly. Code:', event.code, 'Reason:', event.reason);
        if (currentStatus !== 'error' && currentStatus !== 'aborted') {
          this.connectionStatusSubject.next('error');
        }
      }
      this.websocket = null;
    };
  }

  /**
   * Sends a message (query) over the existing WebSocket connection.
   * @param text - The text for the message.
   */
  public sendMessage(text: string): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      const message: { text: string } = { text: text }; // No chat_id needed for WS messages
      try {
        this.websocket.send(JSON.stringify(message));
        console.log("Sent WebSocket message:", message);
        // If status was 'processing_complete', it's now back to 'connected' (actively communicating/waiting for response)
        if(this.connectionStatusSubject.value !== 'connected') {
          this.connectionStatusSubject.next('connected');
        }
      } catch (e) {
        console.error("Error sending WebSocket message:", e);
        this.messageSubject.error(e);
        this.connectionStatusSubject.next('error');
      }
    } else {
      console.error("WebSocket not connected or not open. Cannot send message. Current state:", this.websocket?.readyState);
      this.connectionStatusSubject.next('error'); // Or 'disconnected'
      this.messageSubject.error(new Error("Attempted to send message on non-open WebSocket."));
      // Optionally, try to reconnect if the socket is not open
      // if (!this.websocket || this.websocket.readyState === WebSocket.CLOSED) {
      //   console.log("Attempting to reconnect and send message...");
      //   this.connect(); // This will establish connection
      //   // You might need a mechanism to queue the message and send it once connected.
      //   // For simplicity now, it just errors out.
      // }
    }
  }

  public close(reason: string = "Client initiated disconnect"): void {
    if (this.websocket) {
      const currentState = this.websocket.readyState;
      if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) {
        console.log(`Closing WebSocket connection (state: ${currentState === WebSocket.OPEN ? 'OPEN' : 'CONNECTING'}). Reason: ${reason}`);
        if (currentState === WebSocket.CONNECTING) {
          this.connectionStatusSubject.next('aborted');
        } else {
          this.connectionStatusSubject.next('closed_by_client');
        }
        this.websocket.close(1000, reason);
      } else {
        console.log(`WebSocket is not OPEN or CONNECTING (state: ${currentState}). No action taken by close().`);
      }
    } else {
      console.log("WebSocket instance is null. No connection to close.");
      if (this.connectionStatusSubject.value !== 'disconnected' && this.connectionStatusSubject.value !== 'error') {
        this.connectionStatusSubject.next('disconnected');
      }
    }
  }

  ngOnDestroy(): void {
    console.log("ChatService ngOnDestroy called.");
    this.close("ChatService destroyed by Angular");
    this.messageSubject.complete();
    this.connectionStatusSubject.complete();
    this.serviceSubscriptions.unsubscribe();
  }
}
