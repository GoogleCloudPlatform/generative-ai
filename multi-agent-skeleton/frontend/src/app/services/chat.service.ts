import { Injectable, OnDestroy } from '@angular/core';
import { Subject, Observable, BehaviorSubject, Subscription } from 'rxjs';
import { environment } from 'src/environments/environment';

// Define a type for messages from the server for better type safety
export interface ServerMessage {
  operation?: 'start' | 'close'; // Indicates operational messages
  answer?: any; // For typical bot answers
  intent?: string; // For category intent
  id?: string; // For chat_id or message_id from server
  suggested_questions?: any[]; // For suggested questions
  // Allow other properties for streamed objects
  [key: string]: any;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'reconnecting' | 'closed_by_server' | 'closed_by_client' | 'aborted';

/**
 * Helper function to convert HTTP/HTTPS URL to WS/WSS URL.
 * @param httpUrl The base HTTP/HTTPS URL from environment.backendURL.
 * @returns The WebSocket URL (ws:// or wss://) with the '/api/chats' path appended.
 */
function getWebSocketUrl(httpUrl: string | undefined): string {
  const defaultWsUrl = "ws://localhost:8000/api/chats"; // Fallback if backendURL is not set
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
    // If no protocol, assume http and convert to ws (adjust if default should be https/wss)
    console.warn(`backendURL "${httpUrl}" does not have a standard http/https protocol prefix. Assuming ws://`);
    wsUrl = 'ws://' + httpUrl;
  }

  // Ensure the path is appended correctly, handling potential trailing slashes in the base URL
  if (wsUrl.endsWith('/')) {
    wsUrl = wsUrl + 'chats';
  } else {
    wsUrl = wsUrl + '/chats';
  }

  return wsUrl;
}


@Injectable({
  providedIn: 'root'
})
export class ChatService implements OnDestroy {
  // CHG: Derive WebSocket URL from environment.backendURL, replacing http(s) with ws(s) and appending path.
  private BASE_SOCKET_URL = getWebSocketUrl(environment.backendURL);
  private websocket: WebSocket | null = null;
  private serviceSubscriptions: Subscription = new Subscription();

  // Subject to emit messages received from the WebSocket server
  private messageSubject = new Subject<ServerMessage>();
  // BehaviorSubject to emit the current connection status
  private connectionStatusSubject = new BehaviorSubject<ConnectionStatus>('disconnected');

  constructor() {
    console.log("ChatService (WebSocket) instantiated with URL:", this.BASE_SOCKET_URL); // CHG: Log the derived URL
  }

  /**
   * Returns an observable for messages received from the server.
   */
  public getMessages(): Observable<ServerMessage> {
    return this.messageSubject.asObservable();
  }

  /**
   * Returns an observable for the WebSocket connection status.
   */
  public getConnectionStatus(): Observable<ConnectionStatus> {
    return this.connectionStatusSubject.asObservable();
  }

  // CHG: Removed getAuthToken method as it's no longer needed.
  // private getAuthToken(): string | null { ... }

  /**
   * Establishes a WebSocket connection and sets up event handlers.
   * Sends an initial message with the provided text upon successful connection.
   * @param textForInitialMessage - The text content to send in the first message after connection.
   */
  public connect(textForInitialMessage: string): void {
    if (this.websocket && (this.websocket.readyState === WebSocket.OPEN || this.websocket.readyState === WebSocket.CONNECTING)) {
      console.warn("WebSocket is already open or connecting. Closing existing connection to start a new one.");
      this.close('Client initiated reconnect for new query.');
    }

    this.connectionStatusSubject.next('connecting');
    // CHG: Directly use BASE_SOCKET_URL as auth token logic is removed.
    const socketUrl = this.BASE_SOCKET_URL;
    console.log("Attempting to connect to WebSocket at:", socketUrl);

    // CHG: Removed the block that checked for authToken and modified socketUrl.
    // if (authToken) { ... }

    try { // CHG: Added try-catch around WebSocket creation
      this.websocket = new WebSocket(socketUrl);
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this.connectionStatusSubject.next('error');
      this.messageSubject.error(error);
      return; // Stop execution if WebSocket creation fails
    }


    this.websocket.onopen = (event) => {
      console.log("WebSocket connection established:", event);
      this.connectionStatusSubject.next('connected');

      // CHG: Ensure textToSend is always a string (defaults to empty if null/undefined)
      const textToSend = (textForInitialMessage === undefined || textForInitialMessage === null) ? "" : textForInitialMessage;
      const initialMessage = { text: textToSend }; // CHG: Use textToSend

      try {
        this.websocket?.send(JSON.stringify(initialMessage));
        console.log("Sent initial message:", initialMessage);
        // CHG: Log if default was used
        if (textForInitialMessage === undefined || textForInitialMessage === null) {
          console.warn("textForInitialMessage was null/undefined, sent with empty string in 'text' field.");
        }
      } catch (e) {
        console.error("Error sending initial message:", e);
        this.messageSubject.error(e);
        this.connectionStatusSubject.next('error');
      }
    };;

    this.websocket.onmessage = (event) => {
      try {
        const serverMessage: ServerMessage = JSON.parse(event.data as string);
        console.log("Message from server: ", serverMessage);
        this.messageSubject.next(serverMessage);

        if (serverMessage.operation === "close") {
          this.connectionStatusSubject.next('closed_by_server');
        }
      } catch (e) {
        console.error("Error parsing JSON message from server or received non-JSON message:", event.data, e);
        this.messageSubject.error(new Error(`Failed to parse server message: ${event.data}`));
      }
    };

    this.websocket.onerror = (event) => {
      console.error("WebSocket error observed:", event);
      this.connectionStatusSubject.next('error');
      this.messageSubject.error(event);
    };

    this.websocket.onclose = (event) => {
      console.log("WebSocket connection closed:", event);
      if (event.wasClean) {
        console.log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        if (this.connectionStatusSubject.value !== 'closed_by_server' && this.connectionStatusSubject.value !== 'closed_by_client' && this.connectionStatusSubject.value !== 'aborted') { // CHG: Added check for aborted
          this.connectionStatusSubject.next('disconnected');
        }
      } else {
        console.error('Connection died unexpectedly. Code:', event.code, 'Reason:', event.reason);
        if (this.connectionStatusSubject.value !== 'error') {
          this.connectionStatusSubject.next('error');
        }
      }
      this.websocket = null;
    };
  }

  /**
   * Sends a JSON message to the server if the WebSocket is open.
   */
  public sendMessage(messageObject: any): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      try {
        this.websocket.send(JSON.stringify(messageObject));
        console.log("Sent message to server:", messageObject);
      } catch (e) {
        console.error("Error sending message to server:", e);
        this.messageSubject.error(e);
      }
    } else {
      console.error("WebSocket is not connected or not open. Cannot send message.");
    }
  }

  /**
   * Closes the WebSocket connection if it's open or connecting.
   */
  public close(reason: string = "Client initiated disconnect"): void {
    if (this.websocket) {
      if (this.websocket.readyState === WebSocket.OPEN) {
        console.log(`Closing WebSocket connection (OPEN). Reason: ${reason}`);
        this.connectionStatusSubject.next('closed_by_client');
        this.websocket.close(1000, reason);
      } else if (this.websocket.readyState === WebSocket.CONNECTING) {
        console.log(`Aborting WebSocket connection (CONNECTING). Reason: ${reason}`);
        this.connectionStatusSubject.next('aborted');
        this.websocket.close(1000, reason);
      } else {
        console.log(`WebSocket is neither OPEN nor CONNECTING (state: ${this.websocket.readyState}). No action taken by close().`);
      }
    } else {
      console.log("WebSocket instance is null. No connection to close.");
    }
  }

  /**
   * Lifecycle hook that ensures the WebSocket connection is closed when the service is destroyed.
   */
  ngOnDestroy(): void {
    console.log("ChatService ngOnDestroy called.");
    this.close("ChatService destroyed by Angular");
    this.messageSubject.complete();
    this.connectionStatusSubject.complete();
    this.serviceSubscriptions.unsubscribe();
  }
}
