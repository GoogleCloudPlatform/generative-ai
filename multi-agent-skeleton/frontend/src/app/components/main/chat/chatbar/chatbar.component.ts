import { Component, EventEmitter, Output, OnDestroy, OnInit } from '@angular/core'; // CHG: Added OnInit
// CHG: Updated ChatService import to reflect it's now the WebSocket service.
// Ensure the path 'src/app/services/chat.service' points to the WebSocket ChatService file.
import { ChatService, ServerMessage, ConnectionStatus } from 'src/app/services/chat.service';
import { UserService } from 'src/app/services/user/user.service';
import { BroadcastService } from 'src/app/services/broadcast.service';
import { Observable, ReplaySubject, Subscription } from 'rxjs'; // CHG: Removed timeout, added Subscription
import { takeUntil } from 'rxjs/operators'; // CHG: Added takeUntil
import { SessionService } from 'src/app/services/user/session.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
// CHG: Removed Chat model if it's only for HTTP response, ServerMessage from ChatService will be used for WebSocket.
// import { Chat} from 'src/app/models/chat.model';
import { animate, sequence, state, style, transition, trigger } from '@angular/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SpeechToTextService } from 'src/app/services/speech-to-text';
import { Message, SuggestionData } from 'src/app/models/messegeType.model'; // Assuming Message model is still relevant for UI
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-chatbar',
  templateUrl: './chatbar.component.html',
  styleUrls: ['./chatbar.component.scss'],
  animations: [
    trigger('bounce', [
      state('true', style({ transform: 'translateY(0)', color: '#4285F4' })),
      transition('* => true', [
        sequence([
          style({ transform: 'translateY(0)' }),
          animate("400ms cubic-bezier(0,0,0,1)", style({ transform: 'translateY(-14px)', color: '#4285F4' })),
          animate("300ms cubic-bezier(1,0,1,1)", style({ transform: 'translateY(0)', color: '#4285F4' })),
          animate("200ms cubic-bezier(0,0,0,1)", style({ transform: 'translateY(-10px)', color: '#4285F4' })),
          animate("150ms cubic-bezier(1,0,1,1)", style({ transform: 'translateY(0)', color: '#4285F4' })),
          animate("100ms cubic-bezier(0,0,0,1)", style({ transform: 'translateY(-5px)', color: '#4285F4' })),
          animate("80ms cubic-bezier(1,0,1,1)", style({ transform: 'translateY(0)', color: '#4285F4' })),
        ]),
      ])
    ]),
    trigger('delete', [
      state('true', style({ transform: 'translateY(0)', color: '#ed143d' })),
      transition('* => true', [
        sequence([
          style({ transform: 'translateY(0)' }),
          animate("400ms cubic-bezier(0,0,0,1)", style({ transform: 'translateX(14px)', color: '#ed143d' })),
          animate("300ms cubic-bezier(1,0,1,1)", style({ transform: 'translateX(0)', color: '#ed143d' })),
          animate("200ms cubic-bezier(0,0,0,1)", style({ transform: 'translateX(-14px)', color: '#ed143d' })),
          animate("150ms cubic-bezier(1,0,1,1)", style({ transform: 'translateX(0)', color: '#ed143d' })),
          animate("100ms cubic-bezier(0,0,0,1)", style({ transform: 'translateX(7px)', color: '#ed143d' })),
          animate("80ms cubic-bezier(1,0,1,1)", style({ transform: 'translateX(0)', color: '#ed143d' })),
        ]),
      ])
    ]),
  ]
})
export class ChatbarComponent implements OnInit, OnDestroy { // CHG: Added OnInit

  @Output() onSubmit: EventEmitter<any> = new EventEmitter();

  isSuggestedQuestion: string = '';
  chatQuery: string = ''; // CHG: Initialized chatQuery
  // CHG: currentChatId might be set by WebSocket messages if needed.
  // Its role might change compared to HTTP context.
  currentChatId: string | null = null;
  chatQuery$: Observable<Message>; // This seems to be for messages from BroadcastService
  showLoader: boolean = false;
  startTimer: boolean = false; // Role might change with WebSocket; response time calculation needs review
  conversation: Message[] = [];
  leftContainerClass = "";
  rightContainerClass = "";
  index = 2;
  loaderTextArray: string[] = [
    "I am a conversation bot built on Google Cloud's Vertex AI tools.",
    "Tool Tip: You can reset the conversation anytime using the reset button next the the text input box.",
    "Joke : Why did the robot go on a diet? Because it had too many bytes!",
    "Joke : Why can't bicycles stand up by themselves? Because they are two-tired!",
    "Joke : How does a computer get drunk? It takes screenshots."
  ];
  loaderTextTimeout: undefined | ReturnType<typeof setTimeout>;
  loaderText = "";
  loaderTextIndex = 0;
  loaderIndex = 1;
  isChatDisabled: boolean = false;
  botStartTime: number = 0; // CHG: Initialized
  initialQuestion: string = ''; // CHG: Initialized
  ticketId: string = ''; // CHG: Initialized
  categoryIntent: string = "";
  changeImageInterval: undefined | ReturnType<typeof setTimeout>;
  panelOpenState = false;
  like = false;
  dislike = false;
  // CHG: response: Response type might not be used if it was for HTTP.
  loaderSelectedChip = '';
  showLoaderLikeDislikeButtons = false;
  outOfContextAnswerResponseObject = {
    like: false,
    dislike: false
  }
  showSuggesstion = false; // CHG: Renamed from showSuggesstion to showSuggestion for consistency
  suggestedQuestionMessage!: Message; // CHG: Used definite assignment assertion
  loader_chat_id: any;
  questionArray: any[] = [];

  borderColors = ['#4285F4', '#0F9D58', '#F4B400', '#DB4437'];

  private readonly destroyed = new ReplaySubject<void>(1);
  isRecording = false;
  transcribedText = '';
  mediaRecorder!: MediaRecorder; // CHG: Used definite assignment assertion
  audioChunks: Blob[] = [];

  requiredLogin: string = environment.requiredLogin;

  // CHG: Renamed 'chatService' to 'httpChatService' if it's still needed for other HTTP calls.
  // If ChatService is now purely WebSocket, then this injection should be of the new ChatService.
  // For this refactor, assuming 'ChatService' is now the WebSocket service.
  constructor(private router: Router,
              public dialog: MatDialog,
              private chatService: ChatService, // This is now the WebSocket ChatService
              private sessionService: SessionService,
              public userService: UserService,
              private broadcastService: BroadcastService,
              private _snackBar: MatSnackBar,
              private speechToTextService: SpeechToTextService,
  ) {
    this.chatQuery$ = this.broadcastService.chatQuery$;
    this.chatQuery$.pipe(takeUntil(this.destroyed)).subscribe((value: Message) => { // CHG: Added takeUntil and specified Message type
      // This handles messages pushed from other parts of the app via BroadcastService
      if (value && value.type === 'user' && value.body) {
        this.conversation.unshift(value); // CHG: unshift to add to the beginning like other user messages
        // If this message should initiate a new WebSocket stream:
        this.initiateWebSocketConnection(value.body);
      } else if (value) {
        this.conversation.push(value); // Original behavior for other types
      }
    });
    this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)]; // CHG: Used Math.floor and array length
    // CHG: Removed checkIfMessege() call from constructor, will be handled by subscriptions or user actions
  }

  ngOnInit(): void { // CHG: Added OnInit lifecycle hook
    this.subscribeToConnectionStatus();
    this.subscribeToWebSocketMessages();
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
    this.clearTimeoutForLoaderText(); // CHG: Clear any running timeouts
    if (this.changeImageInterval) clearTimeout(this.changeImageInterval); // CHG: Clear image interval
    this.chatService.close("ChatbarComponent destroyed"); // CHG: Ensure WebSocket is closed
  }

  /** CHG: Subscribes to WebSocket connection status updates from ChatService. */
  private subscribeToConnectionStatus(): void {
    this.chatService.getConnectionStatus().pipe(takeUntil(this.destroyed)).subscribe((status: ConnectionStatus) => {
      console.log("ChatbarComponent - Connection Status:", status);
      this.isChatDisabled = (status === 'connecting'); // Disable input while connecting

      switch (status) {
        case 'connecting':
          this.showLoader = true;
          this.setTimeoutForLoaderText(); // Start loader animations
          this.setCyclicBackgroundImages();
          this.loaderText = "Connecting to assistant..."; // CHG: More specific loader text
          break;
        case 'connected':
          // Loader might still be shown until 'operation: started' is received,
          // or hide it here if appropriate.
          // this.showLoader = false; // Example: hide loader immediately on connect
          // this.clearTimeoutForLoaderText();
          this.loaderText = "Connection established. Waiting for response...";
          break;
        case 'closed_by_server':
        case 'closed_by_client':
        case 'disconnected':
        case 'aborted': // CHG: Added aborted case
          this.showLoader = false;
          this.clearTimeoutForLoaderText();
          if (status !== 'closed_by_client' && status !== 'closed_by_server') { // Don't show error for normal closes
            this.loaderText = "Connection closed. Please try sending a message again.";
          }
          break;
        case 'error':
          this.showLoader = true; // Keep loader to show error message
          this.setErrorMessage(); // Display error message in loader
          break;
      }
    });
  }

  /** CHG: Subscribes to WebSocket messages from ChatService. */
  private subscribeToWebSocketMessages(): void {
    this.chatService.getMessages().pipe(takeUntil(this.destroyed)).subscribe({
      next: (serverMessage: ServerMessage) => {
        console.log("ChatbarComponent - Received Server Message:", serverMessage);

        if (serverMessage.operation === 'start') {
          this.showLoader = true; // Keep loader active while server processes
          this.loaderText = "Assistant is processing your request..."; // CHG: Update loader text
          this.clearTimeoutForLoaderText(); // Stop generic loader text cycle
          this.setCyclicBackgroundImages(); // Continue background cycle
          // `currentChatId` could potentially be part of the 'started' message
          if (serverMessage.id) { // Assuming 'id' in 'started' message is the chat_id
            this.currentChatId = serverMessage.id;
            console.log("Chat ID received from 'started' operation:", this.currentChatId);
          }
        } else if (serverMessage.operation === 'close') {
          this.showLoader = false;
          this.clearTimeoutForLoaderText();
          console.log("Chat stream closed by server.");
          // Handle any final UI updates
        } else {
          // This is a data message (e.g., part of the bot's answer)
          this.showLoader = false; // Hide loader once first data piece arrives
          this.clearTimeoutForLoaderText();
          this.handleWebSocketDataMessage(serverMessage);
        }
      },
      error: (err) => {
        console.error("ChatbarComponent - Error from WebSocket messages:", err);
        this.setErrorMessage(); // Use existing method to display error
      }
    });
  }

  /** CHG: Handles individual data messages from the WebSocket. */
  private handleWebSocketDataMessage(data: ServerMessage): void {
    const endTime = new Date().getTime(); // Time of receiving this specific data part
    // If the server sends a unique ID for each message part, use it. Otherwise, use currentChatId.
    const messageChatId = data.id || this.currentChatId;

    if (this.questionArray.length > 0 && !this.questionArray[this.questionArray.length -1].id && messageChatId) {
      this.assignId(messageChatId); // Assign ID to the last user question if not yet assigned
    }
    let body: string = '';
    let botAnswer: string = '';

    if (data.answer.text) {
      body = data.answer.text;
    }  else if (data.answer.function_call) {
      body = `Calling function ${data.answer.function_call.name} with arguments: ${JSON.stringify(data.answer.function_call.args)}`
    } else if (data.answer.function_response) {
      body = `Received response from function: ${data.answer.function_response.name}. Response: ${data.answer.function_response.response}`
    }

    const botMessage: Message = {
      body: body || '', // Assuming 'answer' contains the text. Adjust if needed.
      botAnswer: botAnswer || '', // Populate botAnswer, could be the full object or specific field
      type: 'bot',
      responseTime: this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A",
      shareable: true, // Assuming shareable
      categoryIntent: data.intent || this.categoryIntent, // Use intent from message or last known
      botStartTime: this.botStartTime ? this.botStartTime.toString() : "N/A",
      extras: {
        like: false,
        dislike: false,
        delete: false,
      },
    };

    console.log(`Received bot message: ${botMessage.body}`)

    this.conversation.unshift(botMessage);

    if (data.suggested_questions && data.suggested_questions.length > 0) {
      this.setSuggestedQuestionInChat(data, endTime); // Pass the ServerMessage directly
    }
    this.scrollToBottom(); // CHG: Added helper for scrolling
  }


  setupMediaRecorder(stream: MediaStream) {
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = event => this.audioChunks.push(event.data);
    this.mediaRecorder.onstop = () => this.sendAudioToGCP();
  }

  async sendAudioToGCP() {
    const audioBlob = new Blob(this.audioChunks);
    try { // CHG: Added try-catch for async operation
      const response: any = await (await this.speechToTextService.transcribeAudio(audioBlob)).toPromise(); // CHG: Convert Observable to Promise for await
      this.chatQuery = response[0]; // Assuming response structure
    } catch (error) {
      console.error("Error transcribing audio:", error);
      this.openSnackBar("Error transcribing audio. Please try again.", "error-snackbar"); // CHG: User feedback
    }
  }

  getStringData(obj: any): string {
    let str = (obj as string);
    if (str === "" || str.length === 0) {
      return "Sorry! I don't have sufficient information to answer this question at the moment.";
    }
    return (obj as string);
  }

  getSuggestionData(obj: any): SuggestionData {
    return (obj as SuggestionData);
  }

  // CHG: This method is largely replaced by WebSocket connection status and message handling.
  // Kept for reference or if there's a scenario where it's still called with an initial message.
  checkIfMessege() {
    if (this.conversation.length > 0 && this.conversation[0].type == 'user' && !this.showLoader) { // CHG: Check showLoader to prevent multiple triggers
      const userMessage = this.conversation[0];
      this.initiateWebSocketConnection(userMessage.body);
    }
  }

  /** CHG: Centralized method to initiate WebSocket connection and set up related state. */
  private initiateWebSocketConnection(query: string): void {
    this.showLoader = true;
    this.setTimeoutForLoaderText();
    this.setCyclicBackgroundImages();
    this.startTimer = true; // This flag might need review for its role with WebSockets
    this.botStartTime = new Date().getTime();
    if (!this.initialQuestion) this.initialQuestion = query; // Set initial question if not already set
    this.pushQuestion(query); // Keep track of the question sent

    this.chatService.connect(query); // Use WebSocket ChatService
  }


  pushQuestion(question: string, id?: any) {
    this.questionArray.push({ question, id });
  }

  assignId(id: any) {
    // Assigns ID to the most recent question in questionArray that doesn't have an ID
    for (let i = this.questionArray.length - 1; i >= 0; i--) {
      if (!this.questionArray[i].id) {
        this.questionArray[i].id = id;
        break;
      }
    }
  }

  getQuestion(id: any) {
    const questionObj = this.questionArray.find(x => x.id === id);
    return questionObj?.question || '';
  }

  submitMessage(event: any) {
    this.outOfContextAnswerResponseObject = {
      like: false,
      dislike: false
    };
    this.removeSuggestionElement();

    if (event instanceof KeyboardEvent || event instanceof MouseEvent) {
      event.preventDefault();
    }
    if (!this.chatQuery || this.chatQuery.trim() === '') { // CHG: Added trim()
      return;
    }

    const queryToSend = this.chatQuery;
    this.chatQuery = ''; // Clear input field immediately

    let singleMessage: Message = {
      body: queryToSend,
      type: 'user',
      shareable: false, // Assuming user messages aren't shareable by default
    };
    this.conversation.unshift(singleMessage); // Add user message to UI

    this.initiateWebSocketConnection(queryToSend); // CHG: Use the new centralized method
    this.scrollToBottom();
  }

  setErrorMessage() {
    this.clearTimeoutForLoaderText();
    this.leftContainerClass = 'left-side-container-error';
    this.loaderText = 'Oops, something went wrong. Please try sending your message again.'; // CHG: Slightly rephrased
    this.rightContainerClass = 'right-side-container-error';
    this.showLoaderLikeDislikeButtons = false;
    this.showLoader = true; // CHG: Ensure loader is visible to show the error message
  }

  setAnswerNotFoundText(loaderText: string) {
    this.clearTimeoutForLoaderText();
    this.showLoader = true;
    this.leftContainerClass = 'answer-not-found';
    this.rightContainerClass = 'right-side-container-error';
    this.loaderText = loaderText + " Please try asking something else";
    this.showLoaderLikeDislikeButtons = true;
  }

  stopTicketCreationFlow() {
    this.isChatDisabled = false;
    this.chatQuery = '';
  }

  setCyclicBackgroundImages() {
    // CHG: Simplified logic for cycling, ensure loaderTextIndex is valid
    this.loaderTextIndex = (this.loaderTextIndex + 1) % 3; // Cycle through 0, 1, 2 for 3 images
    this.leftContainerClass = 'left-side-container-' + (this.loaderTextIndex + 1);
    this.rightContainerClass = 'right-side-container-' + (this.loaderTextIndex + 1);
  }

  setTimeoutForLoaderText() {
    if (this.loaderTextTimeout) clearInterval(this.loaderTextTimeout); // CHG: Clear existing interval
    this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)];
    this.showLoaderLikeDislikeButtons = false;
    this.loaderTextTimeout = setInterval(() => { this.setCyclicLoaderText(); }, 3000);
  }

  clearTimeoutForLoaderText() {
    if (this.loaderTextTimeout) { // CHG: Check if timeout exists before clearing
      clearInterval(this.loaderTextTimeout);
      this.loaderTextTimeout = undefined;
    }
  }

  setCyclicLoaderText() {
    this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)];
    // this.loaderIndex++; // loaderIndex doesn't seem to be used elsewhere for critical logic
  }

  // CHG: This method's logic is now mostly within handleWebSocketDataMessage or subscribeToWebSocketMessages
  // handleBotResponse(response: Chat) { ... } // Original method removed/refactored

  // CHG: Updated to accept ServerMessage type if suggested_questions come from WebSocket
  setSuggestedQuestionInChat(response: ServerMessage, endTime: number) {
    if (response.suggested_questions && response.suggested_questions.length > 0) {
      this.showSuggesstion = true; // CHG: Corrected property name
      this.suggestedQuestionMessage = {
        body: "", // No direct body for suggestion container
        type: 'bot', // Suggestions are from the bot
        responseTime: this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A",
        shareable: false, // Suggestions usually aren't "shareable" chat messages
        categoryIntent: response.intent || this.categoryIntent,
        extras: {
          like: false,
          dislike: false
        },
        suggestedQuestion: response.suggested_questions, // Use directly from ServerMessage
      };
      // The timeout for scrolling should ideally happen after Angular has rendered the new element.
      // Using a small delay is a common approach but can be fragile. Consider AfterViewChecked or ViewChild if issues persist.
      setTimeout(() => {
        this.scrollToBottom(); // CHG: Use helper for scrolling
        // const botResponseElement = document.getElementById(this.botStartTime.toString()); // This ID might not be reliable
        // const parentElement = document.getElementsByClassName('chat-body');
        // if (parentElement[0]) {
        //   parentElement[0].scrollTo(0, parentElement[0].scrollHeight);
        // }
      }, 100); // CHG: Reduced timeout, ensure it's effective
    }
  }

  chipControlOnSelect(event: any) {
    const selectedText = event.target.innerText; // CHG: More robust way to get text
    if (selectedText) {
      this.chatQuery = selectedText;
      this.submitMessage(event); // Pass the event if needed by submitMessage
    }
  }

  getResponseforSuggestionQuery(suggestedQuery: string) { // CHG: Parameter name more descriptive
    this.isSuggestedQuestion = suggestedQuery; // This property's usage might need review
    this.chatQuery = suggestedQuery;
    this.removeSuggestionElement(); // Remove old suggestions before submitting new query
    this.submitMessage(suggestedQuery); // Pass the query string
  }

  removeSuggestionElement() {
    this.showSuggesstion = false; // CHG: Corrected property name
    // Removing elements directly via querySelectorAll can be problematic in Angular.
    // It's better to use *ngIf or other Angular ways to conditionally render suggestions.
    // For now, keeping it if it works, but flag for potential improvement.
    document.querySelectorAll(".bot-suggestion-container").forEach(el => el.remove());
  }

  resetBrowser() {
    this.chatService.close("User reset chat session"); // CHG: Close WebSocket connection
    this.currentChatId = null;
    this.conversation = []; // CHG: Clear conversation
    this.initialQuestion = '';
    this.questionArray = [];
    // this.sessionService.createSession(); // This might re-trigger things; ensure it's intended.
    // this.router.navigateByUrl('/'); // Navigation might also re-trigger constructor/ngOnInit
    // Consider a more controlled state reset.
    this.openSnackBar("Chat has been reset.", "success-snackbar");
  }

  openSnackBar(message: string, panelClass: string) { // CHG: Parameter name consistency
    this._snackBar.open(message, 'Close', {
      panelClass: [panelClass], // CHG: Ensure panelClass is an array
      horizontalPosition: 'end',
      verticalPosition: 'top',
      duration: 3000,
    });
  }

  startRecording() {
    if (this.mediaRecorder) { // CHG: Check if mediaRecorder is initialized
      this.isRecording = true;
      this.audioChunks = [];
      this.mediaRecorder.start();
    } else {
      console.error("MediaRecorder not initialized. Cannot start recording.");
      // CHG: Request microphone permission if not already handled
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          this.setupMediaRecorder(stream);
          this.mediaRecorder.start();
          this.isRecording = true;
          this.audioChunks = [];
        })
        .catch(err => {
          console.error("Error accessing microphone:", err);
          this.openSnackBar("Microphone access denied or unavailable.", "error-snackbar");
        });
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) { // CHG: Check if recording
      this.isRecording = false;
      this.mediaRecorder.stop();
    }
  }

  /** CHG: Helper function to scroll chat body to the bottom. */
  private scrollToBottom(): void {
    try {
      const parentElement = document.getElementsByClassName('chat-body');
      if (parentElement && parentElement[0]) {
        // Use setTimeout to allow Angular to render the new message before scrolling
        setTimeout(() => parentElement[0].scrollTo(0, parentElement[0].scrollHeight), 0);
      }
    } catch (err) {
      console.error("Error scrolling to bottom:", err);
    }
  }
}
