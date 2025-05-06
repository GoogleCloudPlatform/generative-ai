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
import { Message, SuggestionData, ThinkingStep } from 'src/app/models/messegeType.model'; // Import ThinkingStep
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
  private currentBotMessage: Message | null = null; // To hold the message being built

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
            this.currentBotMessage = null; // Current bot turn is complete
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
          // This confirms the backend is ready for the first message of a turn
          // If a user message was just sent, showLoader would be true.
          if (this.showLoader) {
            this.loaderText = "Assistant is processing your request...";
            this.setCyclicBackgroundImages();
          } else { // Auto-connected, no active query from user yet
            this.loaderText = "Assistant is ready.";
            this.showLoader = false; // Ensure loader is off if no query is active
            this.isChatDisabled = false;
          }
          this.clearTimeoutForLoaderText();
          console.log("Chat session turn started by server.");
        } else if (serverMessage.operation === 'end_of_turn') {
          console.log("Server indicated end_of_turn.");
          // The 'processing_complete' status will handle UI changes like hiding loader.
          // Finalize the currentBotMessage if it exists
          if (this.currentBotMessage) {
            // If the body is still empty after all parts, set a placeholder
            if (!this.currentBotMessage.body && (!this.currentBotMessage.thinkingSteps || this.currentBotMessage.thinkingSteps.length === 0)) {
              this.currentBotMessage.body = "[Empty response from assistant]";
            }
            // Update timestamp or any final properties if needed
            const endTime = new Date().getTime();
            this.currentBotMessage.responseTime = this.botStartTime ? ((endTime - this.botStartTime) / 1000).toString() : "N/A";
          }
          this.currentBotMessage = null; // Reset for the next turn
        } else if (serverMessage.error) {
          console.error("Error message from server:", serverMessage.error);
          this.setErrorMessage(serverMessage.error);
          this.currentBotMessage = null;
        } else if (serverMessage.answer) {
          this.showLoader = false; // Hide main loader once first answer part arrives
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

    // Ensure there's a current bot message to append to, or create one
    if (!this.currentBotMessage || this.conversation[0] !== this.currentBotMessage) {
      // This condition implies a new bot turn is starting
      this.currentBotMessage = {
        body: '',
        type: 'bot',
        shareable: true,
        categoryIntent: data.intent || this.categoryIntent,
        botStartTime: this.botStartTime ? this.botStartTime.toString() : "N/A",
        extras: { like: false, dislike: false, delete: false },
        thinkingSteps: [], // Initialize thinking steps
        // responseTime will be set at end_of_turn
      };
      this.conversation.unshift(this.currentBotMessage);
    }

    const activeBotMessage = this.currentBotMessage; // Use the message being built

    if (data.answer && data.answer.function_call) {
      activeBotMessage.thinkingSteps = activeBotMessage.thinkingSteps || [];
      activeBotMessage.thinkingSteps.push({
        type: 'functionCall',
        name: data.answer.function_call.name,
        data: data.answer.function_call.args,
      });
    } else if (data.answer && data.answer.function_response) {
      activeBotMessage.thinkingSteps = activeBotMessage.thinkingSteps || [];
      activeBotMessage.thinkingSteps.push({
        type: 'functionResponse',
        name: data.answer.function_response.name,
        data: data.answer.function_response.response,
      });
    } else if (data.answer && typeof data.answer.text === 'string') {
      activeBotMessage.body = (activeBotMessage.body || '') + data.answer.text; // Append text parts
    } else if (typeof data.answer === 'string') {
      activeBotMessage.body = (activeBotMessage.body || '') + data.answer;
    } else if (data.answer && Object.keys(data.answer).length > 0) {
      console.warn("Received answer object with unknown structure, adding to thinking steps:", data.answer);
      activeBotMessage.thinkingSteps = activeBotMessage.thinkingSteps || [];
      activeBotMessage.thinkingSteps.push({
        type: 'functionResponse', // Or a generic 'toolOutput' type
        name: 'Unknown Tool Output',
        data: data.answer,
      });
    } else {
      console.log("Received WS data part without actionable content for current message:", data);
    }

    // Update intent if provided with any part
    if (data.intent) {
      activeBotMessage.categoryIntent = data.intent;
    }

    if (data.suggested_questions && data.suggested_questions.length > 0) {
      // Suggested questions are usually at the end, associate with the completed message
      activeBotMessage.suggestedQuestion = data.suggested_questions;
      // this.setSuggestedQuestionInChat(data, new Date().getTime()); // This might create a separate suggestion card
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
    this.currentBotMessage = null; // Reset current bot message for the new turn

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

  // This method might need adjustment if suggested questions are part of the main bot message object
  setSuggestedQuestionInChat(response: ServerMessage, endTime: number) {
    if (this.currentBotMessage && response.suggested_questions && response.suggested_questions.length > 0) {
      this.currentBotMessage.suggestedQuestion = response.suggested_questions;
      // If you still want a separate suggestion card, this logic would need to be different
      // For now, let's assume suggested questions are part of the currentBotMessage
      this.showSuggestion = true; // This might control a global suggestion display area
      this.suggestedQuestionMessage = this.currentBotMessage; // Or map to a specific structure
      setTimeout(() => { this.scrollToBottom(); }, 100);
    } else if (response.suggested_questions && response.suggested_questions.length > 0) {
      // Fallback if currentBotMessage isn't set, though it should be
      this.showSuggestion = true;
      this.suggestedQuestionMessage = { // Create a temporary message for suggestions
        body: "", // No body for this separate suggestion card
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
