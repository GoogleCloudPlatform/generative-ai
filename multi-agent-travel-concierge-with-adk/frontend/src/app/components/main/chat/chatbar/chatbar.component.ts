// /usr/local/google/home/switon/dev/quick-bot-app/multi-agent-skeleton/frontend/src/app/components/main/chat/chatbar/chatbar.component.ts
import { Component, EventEmitter, Output, OnDestroy, OnInit } from '@angular/core';
import { ChatService, ServerMessage, ConnectionStatus } from 'src/app/services/chat.service';
import { UserService } from 'src/app/services/user/user.service';
import { BroadcastService } from 'src/app/services/broadcast.service';
import { Observable, ReplaySubject, Subscription, firstValueFrom } from 'rxjs';
import { takeUntil, distinctUntilChanged } from 'rxjs/operators';
import { SessionService } from 'src/app/services/user/session.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { animate, sequence, state, style, transition, trigger } from '@angular/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SpeechToTextService } from 'src/app/services/speech-to-text';
// Import MessageContentPart and ThinkingStep
import { Message, SuggestionData, ThinkingStep, MessageContentPart } from 'src/app/models/messegeType.model';
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

  private currentConnectionStatus: ConnectionStatus = 'disconnected';
  private currentBotMessage: Message | null = null;

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
      if (value && value.type === 'user' && value.contentParts[0].text) { // Ensure body exists for user messages
        this.conversation.unshift(value);
        if (this.currentConnectionStatus === 'connected' || this.currentConnectionStatus === 'processing_complete') {
          this.chatService.sendMessage(value.contentParts[0].text);
        } else {
          console.warn("Broadcast message received, but WebSocket not in a ready state to send immediately. Ensure connect() is called.");
        }
      } else if (value) { // Handle other broadcasted message types if necessary
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

  public getPlaceDisplayUrl(place: any): string {
    // if (place && place.image_url) {
    //   return place.image_url; // Prioritize the provided image_url
    // }
    
    // Fallback to Unsplash Source if no image_url or if it's empty
    // Use keywords from place_name. Adjust dimensions (100x100) as needed.
    const keywords = place.place_name.split(' ').join(',').toLowerCase();
    return `https://maps.googleapis.com/maps/api/staticmap?center=${encodeURIComponent(keywords)}&zoom=14&size=200x200&key=${environment.googleMapsApiKey}`;
    
  }

  private subscribeToConnectionStatus(): void {
    this.chatService.getConnectionStatus()
      .pipe(
        takeUntil(this.destroyed),
        distinctUntilChanged()
      )
      .subscribe((status: ConnectionStatus) => {
        console.log("ChatbarComponent - Connection Status:", status);
        this.currentConnectionStatus = status;
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
            // currentBotMessage is finalized when 'end_of_turn' is received
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
            this.currentBotMessage = null;
            break;
          case 'error':
            this.setErrorMessage("An error occurred with the connection.");
            this.isChatDisabled = false;
            this.currentBotMessage = null;
            break;
        }
      });
  }

  private subscribeToWebSocketMessages(): void {
    this.chatService.getMessages().pipe(takeUntil(this.destroyed)).subscribe({
      next: (serverMessage: ServerMessage) => {
        console.log("ChatbarComponent - Received Server Message:", serverMessage);

        if (serverMessage.operation === 'start') {
          if (this.showLoader) { // A user query is active
            this.loaderText = "Assistant is processing your request...";
            this.setCyclicBackgroundImages();
          } else { // Auto-connected, no active query
            this.loaderText = "Assistant is ready.";
            this.showLoader = false;
            this.isChatDisabled = false;
          }
          this.clearTimeoutForLoaderText();
          console.log("Chat session turn started by server.");
        } else if (serverMessage.operation === 'end_of_turn') {
          console.log("Server indicated end_of_turn.");
          if (this.currentBotMessage) {
            const endTime = new Date().getTime();
            this.currentBotMessage.responseTime = this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A";
            // Ensure there's some content if nothing else was added
            if (this.currentBotMessage.contentParts.length === 0) {
              this.currentBotMessage.contentParts.push({type: 'text', text: "[Empty response]"});
            }
          }
          // The 'processing_complete' status will reset currentBotMessage
        } else if (serverMessage.error) {
          console.error("Error message from server:", serverMessage.error);
          this.setErrorMessage(serverMessage.error);
          this.currentBotMessage = null;
        } else if (serverMessage.answer) {
          this.showLoader = false;
          this.clearTimeoutForLoaderText();
          this.handleWebSocketDataMessage(serverMessage);
        } else {
          console.warn("Received unhandled server message structure:", serverMessage);
        }
      },
      error: (err) => {
        console.error("ChatbarComponent - Error from WebSocket messages observable:", err);
        this.setErrorMessage("Failed to process message from server.");
        this.currentBotMessage = null;
      }
    });
  }

  private handleWebSocketDataMessage(data: ServerMessage): void {
    console.log("ChatbarComponent - Handling WebSocket Data Message:", data);

    if (!this.currentBotMessage || this.conversation[0] !== this.currentBotMessage) {
      this.currentBotMessage = {
        contentParts: [], // Initialize with contentParts
        type: 'bot',
        shareable: true,
        categoryIntent: data.intent || this.categoryIntent,
        botStartTime: this.botStartTime ? this.botStartTime.toString() : "N/A",
        extras: { like: false, dislike: false, delete: false },
      };
      this.conversation.unshift(this.currentBotMessage);
    }

    const activeBotMessage = this.currentBotMessage;
    let lastPart = activeBotMessage.contentParts.length > 0 ? activeBotMessage.contentParts[activeBotMessage.contentParts.length - 1] : null;

    if (data.answer && data.answer.function_call) {
      const thinkingStep: ThinkingStep = {
        type: 'functionCall',
        name: data.answer.function_call.name,
        data: data.answer.function_call.args,
      };
      if (lastPart && lastPart.type === 'thinking') {
        lastPart.thinkingSteps = lastPart.thinkingSteps || [];
        lastPart.thinkingSteps.push(thinkingStep);
      } else {
        activeBotMessage.contentParts.push({ type: 'thinking', thinkingSteps: [thinkingStep] });
      }
    } else if (data.answer && data.answer.function_response) {
      const thinkingStep: ThinkingStep = {
        type: 'functionResponse',
        name: data.answer.function_response.name,
        data: data.answer.function_response.response,
      };
      if (lastPart && lastPart.type === 'thinking') {
        lastPart.thinkingSteps = lastPart.thinkingSteps || [];
        lastPart.thinkingSteps.push(thinkingStep);
      } else {
        // This case might be less common if a function_call always precedes a response
        // but good to handle if a response can start a thinking block.
        activeBotMessage.contentParts.push({ type: 'thinking', thinkingSteps: [thinkingStep] });
      }
    } else if (data.answer && typeof data.answer.text === 'string') {
      if (lastPart && lastPart.type === 'text') {
        lastPart.text += data.answer.text; // Append to existing text part
      } else {
        activeBotMessage.contentParts.push({ type: 'text', text: data.answer.text });
      }
    } else if (typeof data.answer === 'string') { // Fallback for plain string answer
      if (lastPart && lastPart.type === 'text') {
        lastPart.text += data.answer;
      } else {
        activeBotMessage.contentParts.push({ type: 'text', text: data.answer });
      }
    } else if (data.answer && Object.keys(data.answer).length > 0) {
      console.warn("Received answer object with unknown structure, adding as new thinking step:", data.answer);
      const thinkingStep: ThinkingStep = {
        type: 'functionResponse', // Treat as a generic tool output
        name: 'Unknown Tool Output',
        data: data.answer,
      };
      if (lastPart && lastPart.type === 'thinking') {
        lastPart.thinkingSteps = lastPart.thinkingSteps || [];
        lastPart.thinkingSteps.push(thinkingStep);
      } else {
        activeBotMessage.contentParts.push({ type: 'thinking', thinkingSteps: [thinkingStep] });
      }
    } else {
      console.log("Received WS data part without actionable content for current message:", data);
    }

    if (data.intent) {
      activeBotMessage.categoryIntent = data.intent;
    }
    if (data.suggested_questions && data.suggested_questions.length > 0) {
      activeBotMessage.suggestedQuestion = data.suggested_questions;
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
      contentParts: [{ type: 'text', text: queryToSend }], // User message is simple text
      type: 'user',
      shareable: false,
    };
    this.conversation.unshift(userMessage);
    this.currentBotMessage = null;

    if (this.currentConnectionStatus === 'connected' || this.currentConnectionStatus === 'processing_complete') {
      this.showLoader = true;
      this.loaderText = "Sending your message...";
      this.setTimeoutForLoaderText();
      this.setCyclicBackgroundImages();
      this.botStartTime = new Date().getTime();
      this.pushQuestion(queryToSend);

      console.log("submitMessage: Sending message via WebSocket.");
      this.chatService.sendMessage(queryToSend);
    } else {
      console.error("submitMessage: WebSocket not in a ready state to send message. Status:", this.currentConnectionStatus);
      this.setErrorMessage("Cannot send message. Connection not ready. Please try again.");
      if (this.currentConnectionStatus === 'disconnected' || this.currentConnectionStatus === 'error' || this.currentConnectionStatus === 'aborted') {
        this.chatService.connect();
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
    this.currentBotMessage = null;
    this.openSnackBar("Chat has been reset.", "success-snackbar");

    setTimeout(() => this.chatService.connect(), 100);
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
    if (this.currentBotMessage && response.suggested_questions && response.suggested_questions.length > 0) {
      this.currentBotMessage.suggestedQuestion = response.suggested_questions;
      this.showSuggestion = true;
      this.suggestedQuestionMessage = this.currentBotMessage;
      setTimeout(() => { this.scrollToBottom(); }, 100);
    } else if (response.suggested_questions && response.suggested_questions.length > 0) {
      this.showSuggestion = true;
      this.suggestedQuestionMessage = {
        contentParts: [],
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
