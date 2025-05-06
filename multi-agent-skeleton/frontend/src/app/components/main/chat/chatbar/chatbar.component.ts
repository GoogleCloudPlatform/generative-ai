// /usr/local/google/home/switon/dev/quick-bot-app/multi-agent-skeleton/frontend/src/app/components/main/chat/chatbar/chatbar.component.ts
import { Component, EventEmitter, Output, OnDestroy, OnInit } from '@angular/core';
import { ChatService, ServerMessage, ConnectionStatus } from 'src/app/services/chat.service';
import { UserService } from 'src/app/services/user/user.service';
import { BroadcastService } from 'src/app/services/broadcast.service';
import { Observable, ReplaySubject, Subscription, firstValueFrom } from 'rxjs'; // Added firstValueFrom
import { takeUntil, distinctUntilChanged } from 'rxjs/operators';
import { SessionService } from 'src/app/services/user/session.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { animate, sequence, state, style, transition, trigger } from '@angular/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SpeechToTextService } from 'src/app/services/speech-to-text';
import { Message, SuggestionData } from 'src/app/models/messegeType.model';
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
export class ChatbarComponent implements OnInit, OnDestroy {

  @Output() onSubmit: EventEmitter<Message> = new EventEmitter<Message>();

  isSuggestedQuestion: string = '';
  chatQuery: string = '';
  chatQuery$: Observable<Message>;
  showLoader: boolean = false;
  startTimer: boolean = false;
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
  botStartTime: number = 0;
  initialQuestion: string = '';
  ticketId: string = '';
  categoryIntent: string = "";
  changeImageInterval: undefined | ReturnType<typeof setTimeout>;
  panelOpenState = false;
  like = false;
  dislike = false;
  loaderSelectedChip = '';
  showLoaderLikeDislikeButtons = false;
  outOfContextAnswerResponseObject = {
    like: false,
    dislike: false
  }
  showSuggestion = false;
  suggestedQuestionMessage!: Message;
  loader_chat_id: any;
  questionArray: { question: string, id?: any }[] = [];

  borderColors = ['#4285F4', '#0F9D58', '#F4B400', '#DB4437'];

  private readonly destroyed = new ReplaySubject<void>(1);
  isRecording = false;
  transcribedText = '';
  mediaRecorder!: MediaRecorder;
  audioChunks: Blob[] = [];

  requiredLogin: string = environment.requiredLogin;

  // Property to store the current connection status
  private currentConnectionStatus: ConnectionStatus = 'disconnected';

  constructor(private router: Router,
              public dialog: MatDialog,
              private chatService: ChatService,
              private sessionService: SessionService,
              public userService: UserService,
              private broadcastService: BroadcastService,
              private _snackBar: MatSnackBar,
              private speechToTextService: SpeechToTextService,
  ) {
    this.chatQuery$ = this.broadcastService.chatQuery$;
    this.chatQuery$.pipe(takeUntil(this.destroyed)).subscribe((value: Message) => {
      if (value && value.type === 'user' && value.body) {
        this.conversation.unshift(value);
        // Use the stored currentConnectionStatus
        if (this.currentConnectionStatus === 'connected' || this.currentConnectionStatus === 'processing_complete') {
          this.chatService.sendMessage(value.body);
        } else {
          console.warn("Broadcast message received, but WebSocket not in a ready state to send immediately. Ensure connect() is called.");
        }
      } else if (value) {
        this.conversation.push(value);
      }
    });
    this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)];
  }

  ngOnInit(): void {
    this.chatService.connect();
    this.subscribeToConnectionStatus();
    this.subscribeToWebSocketMessages();
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
    this.clearTimeoutForLoaderText();
    if (this.changeImageInterval) clearTimeout(this.changeImageInterval);
    this.chatService.close("ChatbarComponent destroyed");
  }

  private subscribeToConnectionStatus(): void {
    this.chatService.getConnectionStatus()
      .pipe(
        takeUntil(this.destroyed),
        distinctUntilChanged()
      )
      .subscribe((status: ConnectionStatus) => {
        console.log("ChatbarComponent - Connection Status:", status);
        this.currentConnectionStatus = status; // Store the latest status
        this.isChatDisabled = (status === 'connecting' || status === 'reconnecting');

        switch (status) {
          case 'connecting':
          case 'reconnecting':
            this.showLoader = true;
            this.loaderText = status === 'connecting' ? "Connecting to assistant..." : "Reconnecting...";
            this.setCyclicBackgroundImages();
            break;
          case 'connected':
            this.loaderText = "Connection established. Assistant is ready.";
            if (!this.showLoader) {
              this.isChatDisabled = false;
            }
            break;
          case 'processing_complete':
            this.showLoader = false;
            this.clearTimeoutForLoaderText();
            this.loaderText = "Assistant is ready for your next message.";
            this.isChatDisabled = false;
            break;
          case 'closed_by_server':
          case 'closed_by_client':
          case 'disconnected':
          case 'aborted':
            this.showLoader = false;
            this.clearTimeoutForLoaderText();
            if (status === 'disconnected' && this.conversation.length > 0 && this.conversation[0]?.type === 'user' && !this.showLoader) {
              this.setErrorMessage("Connection lost. Please try sending your message again.");
            } else if (status === 'closed_by_server') {
              this.loaderText = "Connection closed by server.";
            } else if (status === 'closed_by_client' && this.conversation.length > 0) {
              this.loaderText = "Chat session ended.";
            }
            this.isChatDisabled = false;
            break;
          case 'error':
            this.setErrorMessage("An error occurred with the connection.");
            this.isChatDisabled = false;
            break;
        }
      });
  }

  private subscribeToWebSocketMessages(): void {
    this.chatService.getMessages().pipe(takeUntil(this.destroyed)).subscribe({
      next: (serverMessage: ServerMessage) => {
        console.log("ChatbarComponent - Received Server Message:", serverMessage);

        if (serverMessage.operation === 'start') {
          if (!this.showLoader) { // If user hasn't sent a message yet
            this.loaderText = "Assistant is ready.";
            // No loader needed if just connecting and no active query
            this.showLoader = false;
            this.isChatDisabled = false;
          } else { // If user sent a message and this 'start' is the ack
            this.loaderText = "Assistant is processing your request...";
            this.setCyclicBackgroundImages();
          }
          this.clearTimeoutForLoaderText(); // Stop generic loader text if any
          console.log("Chat session started by server.");
          // this.isChatDisabled = false; // Ensure chat is enabled
        } else if (serverMessage.operation === 'end_of_turn') {
          console.log("Server indicated end_of_turn.");
          // UI updates (like hiding loader and enabling input) are handled by 'processing_complete' status
        } else if (serverMessage.error) {
          console.error("Error message from server:", serverMessage.error);
          this.setErrorMessage(serverMessage.error);
        } else if (serverMessage.answer) { // This is a data/answer message
          this.showLoader = false; // Hide loader once first actual answer part arrives
          this.clearTimeoutForLoaderText(); // Stop generic loader text
          this.handleWebSocketDataMessage(serverMessage);
        } else {
          console.warn("Received unhandled server message structure:", serverMessage);
        }
      },
      error: (err) => {
        console.error("ChatbarComponent - Error from WebSocket messages observable:", err);
        this.setErrorMessage("Failed to process message from server.");
      }
    });
  }

  private handleWebSocketDataMessage(data: ServerMessage): void {
    console.log("ChatbarComponent - Handling WebSocket Data Message:", data);
    const endTime = new Date().getTime();

    const botMessage: Message = {
      body: '', // Initialize body, will be populated based on content type
      type: 'bot',
      responseTime: this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A",
      shareable: true, // Assuming all bot messages are shareable by default
      categoryIntent: data.intent || this.categoryIntent,
      botStartTime: this.botStartTime ? this.botStartTime.toString() : "N/A",
      extras: { like: false, dislike: false, delete: false },
      // functionCall and functionResponse will be set below
    };

    if (data.answer && data.answer.function_call) {
      botMessage.functionCall = {
        name: data.answer.function_call.name,
        args: data.answer.function_call.args,
      };
      // Optionally, set a placeholder or summary in the main body if desired
      // botMessage.body = `Executing: ${data.answer.function_call.name}`;
    } else if (data.answer && data.answer.function_response) {
      botMessage.functionResponse = {
        name: data.answer.function_response.name,
        response: data.answer.function_response.response,
      };
      // botMessage.body = `Received result from: ${data.answer.function_response.name}`;
    } else if (data.answer && typeof data.answer.text === 'string') {
      botMessage.body = data.answer.text;
    } else if (typeof data.answer === 'string') { // Fallback if answer is just a string
      botMessage.body = data.answer;
    } else if (Object.keys(data.answer || {}).length > 0) { // If answer is an object but not function call/response/text
      console.warn("Received answer object with unknown structure:", data.answer);
      // Attempt to stringify if it's a simple object, otherwise show placeholder
      try {
        const stringified = JSON.stringify(data.answer);
        if (stringified.length < 200) { // Arbitrary length limit
          botMessage.body = stringified;
        } else {
          botMessage.body = "[Structured content received]";
        }
      } catch (e) {
        botMessage.body = "[Complex content received]";
      }
    } else {
      console.warn("Received empty or unhandled answer content:", data.answer);
      botMessage.body = ""; // Or a placeholder like "[Empty Response]"
    }

    // Only add message to conversation if it has a body or a function call/response
    if (botMessage.body || botMessage.functionCall || botMessage.functionResponse) {
      console.log(`Adding bot message to conversation. Body: "${botMessage.body}", FC: ${!!botMessage.functionCall}, FR: ${!!botMessage.functionResponse}`);
      this.conversation.unshift(botMessage);
    } else {
      console.log("Skipping empty bot message from WS data:", data);
    }


    if (data.suggested_questions && data.suggested_questions.length > 0) {
      this.setSuggestedQuestionInChat(data, endTime);
    }
    this.scrollToBottom();
  }

  submitMessage(event: any) {
    this.outOfContextAnswerResponseObject = { like: false, dislike: false };
    this.removeSuggestionElement();

    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }

    const queryToSend = this.chatQuery.trim();
    if (!queryToSend) {
      return;
    }
    this.chatQuery = '';

    const userMessage: Message = {
      body: queryToSend,
      type: 'user',
      shareable: false,
    };
    this.conversation.unshift(userMessage);

    // Use the stored currentConnectionStatus
    if (this.currentConnectionStatus === 'connected' || this.currentConnectionStatus === 'processing_complete') {
      this.showLoader = true;
      this.loaderText = "Sending your message..."; // More accurate text
      this.setTimeoutForLoaderText(); // Start loader text cycle
      this.setCyclicBackgroundImages();
      this.botStartTime = new Date().getTime();
      this.pushQuestion(queryToSend);

      console.log("submitMessage: Sending message via WebSocket.");
      this.chatService.sendMessage(queryToSend);
    } else {
      console.error("submitMessage: WebSocket not in a ready state to send message. Status:", this.currentConnectionStatus);
      this.setErrorMessage("Cannot send message. Connection not ready. Please try again.");
      if (this.currentConnectionStatus === 'disconnected' || this.currentConnectionStatus === 'error' || this.currentConnectionStatus === 'aborted') {
        this.chatService.connect(); // Attempt to re-establish connection
      }
    }
    this.scrollToBottom();
  }

  setErrorMessage(customMessage?: string) {
    this.clearTimeoutForLoaderText();
    this.leftContainerClass = 'left-side-container-error';
    this.loaderText = customMessage || 'Oops, something went wrong. Please try sending your message again.';
    this.rightContainerClass = 'right-side-container-error';
    this.showLoaderLikeDislikeButtons = false;
    this.showLoader = true;
  }

  resetBrowser() {
    console.log("Chatbar: Resetting chat session.");
    this.chatService.close("User reset chat session");
    this.conversation = [];
    this.initialQuestion = '';
    this.questionArray = [];
    this.showLoader = false;
    this.isChatDisabled = false;
    this.clearTimeoutForLoaderText();
    this.removeSuggestionElement();
    this.openSnackBar("Chat has been reset.", "success-snackbar");

    setTimeout(() => this.chatService.connect(), 100); // Reconnect after reset
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
      this.openSnackBar("Error transcribing audio. Please try again.", "error-snackbar");
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

  assignId(id: any) {
    for (let i = this.questionArray.length - 1; i >= 0; i--) {
      if (!this.questionArray[i].id) {
        this.questionArray[i].id = id;
        break;
      }
    }
  }
  getQuestion(id: any) { return '';}
  setAnswerNotFoundText(loaderText: string) { }
  stopTicketCreationFlow() { }
  setCyclicBackgroundImages() { }
  setTimeoutForLoaderText() {
    if (this.loaderTextTimeout) clearInterval(this.loaderTextTimeout);
    this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)];
    this.showLoaderLikeDislikeButtons = false;
    this.loaderTextTimeout = setInterval(() => { this.setCyclicLoaderText(); }, 3000);
  }
  clearTimeoutForLoaderText() { if (this.loaderTextTimeout) { clearInterval(this.loaderTextTimeout); this.loaderTextTimeout = undefined; } }
  setCyclicLoaderText() { this.loaderText = this.loaderTextArray[Math.floor(Math.random() * this.loaderTextArray.length)]; }
  setSuggestedQuestionInChat(response: ServerMessage, endTime: number) {
    if (response.suggested_questions && response.suggested_questions.length > 0) {
      this.showSuggestion = true;
      this.suggestedQuestionMessage = {
        body: "",
        type: 'bot',
        responseTime: this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A",
        shareable: false,
        categoryIntent: response.intent || this.categoryIntent,
        extras: { like: false, dislike: false },
        suggestedQuestion: response.suggested_questions,
      };
      setTimeout(() => { this.scrollToBottom(); }, 100);
    }
  }
  chipControlOnSelect(event: any) {
    const selectedText = event.target.innerText;
    if (selectedText) {
      this.chatQuery = selectedText;
      this.submitMessage(event);
    }
  }
  getResponseforSuggestionQuery(suggestedQuery: string) {
    this.isSuggestedQuestion = suggestedQuery;
    this.chatQuery = suggestedQuery;
    this.removeSuggestionElement();
    this.submitMessage(suggestedQuery);
  }
  removeSuggestionElement() { this.showSuggestion = false; }
  openSnackBar(message: string, panelClass: string) {
    this._snackBar.open(message, 'Close', {
      panelClass: [panelClass],
      horizontalPosition: 'end',
      verticalPosition: 'top',
      duration: 3000,
    });
  }
  startRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === "inactive") {
      this.isRecording = true;
      this.audioChunks = [];
      this.mediaRecorder.start();
    } else if (!this.mediaRecorder) {
      console.warn("MediaRecorder not initialized. Attempting to initialize...");
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          this.setupMediaRecorder(stream);
          if (this.mediaRecorder && this.mediaRecorder.state === "inactive") {
            this.isRecording = true;
            this.audioChunks = [];
            this.mediaRecorder.start();
          }
        })
        .catch(err => {
          console.error("Error accessing microphone:", err);
          this.openSnackBar("Microphone access denied or unavailable.", "error-snackbar");
        });
    } else {
      console.warn("MediaRecorder is already recording or in an unexpected state:", this.mediaRecorder.state);
    }
  }
  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.isRecording = false;
      this.mediaRecorder.stop();
    }
  }
  scrollToBottom(): void {
    try {
      const parentElement = document.getElementsByClassName('chat-body');
      if (parentElement && parentElement[0]) {
        setTimeout(() => parentElement[0].scrollTo(0, parentElement[0].scrollHeight), 0);
      }
    } catch (err) {
      console.error("Error scrolling to bottom:", err);
    }
  }
  pushQuestion(question: string, id?: any) {
    this.questionArray.push({ question, id });
  }
}
