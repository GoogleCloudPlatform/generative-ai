import { Component, EventEmitter, Output, OnDestroy } from '@angular/core';
import { ChatService } from 'src/app/services/chat.service';
import { UserService } from 'src/app/services/user/user.service';
import { BroadcastService } from 'src/app/services/broadcast.service';
import { Observable, timeout, ReplaySubject } from 'rxjs';
import { SessionService } from 'src/app/services/user/session.service';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Chat} from 'src/app/models/chat.model';
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
export class ChatbarComponent implements OnDestroy {

  @Output() onSubmit: EventEmitter<any> = new EventEmitter();

  isSuggestedQuestion: string = '';
  chatQuery: string
  currentChatId: string | null = null;
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
  botStartTime: number;
  initialQuestion: string;
  ticketId: string;
  categoryIntent: string = "";
  changeImageInterval: undefined | ReturnType<typeof setTimeout>;
  panelOpenState = false;
  like = false;
  dislike = false;
  response: Response
  loaderSelectedChip = '';
  showLoaderLikeDislikeButtons = false;
  outOfContextAnswerResponseObject = {
    like: false,
    dislike: false
  }
  showSuggesstion = false;
  suggestedQuestionMessage: Message;
  loader_chat_id: any;
  questionArray: any[] = [];

  /** DEP accordion border colors */
  borderColors = ['#4285F4', '#0F9D58', '#F4B400', '#DB4437'];

  private readonly destroyed = new ReplaySubject<void>(1);
  isRecording = false;
  transcribedText = '';
  mediaRecorder: MediaRecorder;
  audioChunks: Blob[] = [];

  requiredLogin: string = environment.requiredLogin

  constructor(private router: Router,
    public dialog: MatDialog,
    private chatService: ChatService,
    private sessionService: SessionService,
    public userService: UserService,
    private broadcastService: BroadcastService,
    private _snackBar: MatSnackBar,
    private speechToTextService: SpeechToTextService,
  ) {
    this.chatQuery$ = this.broadcastService.chatQuery$
    this.chatQuery$.subscribe((value: any) => {
      this.conversation.push(value);
    });
    this.loaderText = this.loaderTextArray[Math.round(Math.random() * 10)];
    this.checkIfMessege();
  }

  setupMediaRecorder(stream: MediaStream) {
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = event => this.audioChunks.push(event.data);
    this.mediaRecorder.onstop = () => this.sendAudioToGCP();
  }

  async sendAudioToGCP() {
    const audioBlob = new Blob(this.audioChunks);
    // console.log(audioBlob);
    (await this.speechToTextService.transcribeAudio(audioBlob)).subscribe(
      (response: any) => {
        // console.log(response)
        this.chatQuery = response[0]
      },
      (error: any) => {
        // Handle errors
      }
    );
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
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

  checkIfMessege() {
    if (this.conversation.length == 1 && this.conversation[0].type == 'user') {
      this.showLoader = true;
      this.setTimeoutForLoaderText();
      this.setCyclicBackgroundImages();
      this.startTimer = true;
      this.botStartTime = new Date().getTime()
      this.initialQuestion = this.conversation[0].body;
      this.pushQuestion(this.initialQuestion);
      this.chatService.postChat(this.conversation[0].body).pipe(timeout(90000)).subscribe({
        next: (response: Chat) => this.handleBotResponse(response),
        error: (err) => {
          this.setErrorMessage();
        }
      })
    }
  }

  pushQuestion(question: string, id?: any) {
    this.questionArray.push({ question, id });
  }

  assignId(id: any) {
    for (let i = 0; i < this.questionArray.length; i++) {
      if (!this.questionArray[i].id) {
        this.questionArray[i].id = id;
        break;
      }
    };
  }

  getQuestion(id: any) {
    const questionObj = this.questionArray.find(x => x.id === id);
    return questionObj?.question || '';
  }

  async submitMessage(event: any) {
    this.outOfContextAnswerResponseObject = {
      like: false,
      dislike: false
    };
    this.removeSuggestionElement();
    this.pushQuestion(this.chatQuery);

    this.botStartTime = new Date().getTime();
    // keeps the scrollbar to the bottom
    const parentElement = document.getElementsByClassName('chat-body');
    parentElement[0].scrollTo(0, parentElement[0].scrollHeight);

    if (event instanceof KeyboardEvent || event instanceof MouseEvent) {
      event.preventDefault();
    }
    if (!this.chatQuery || this.chatQuery === '') {
      return;
    }
    if (!this.initialQuestion) this.initialQuestion = this.chatQuery;

    let singleMessage: Message = {
      body: this.chatQuery,
      type: 'user',
      shareable: false,
    }

    this.conversation.unshift(singleMessage);
    this.chatQuery = '';
    this.showLoader = true;
    this.setTimeoutForLoaderText();
    this.setCyclicBackgroundImages();
    this.chatService.postChat(singleMessage.body, this.currentChatId).pipe(timeout(90000)).subscribe({
      next: (response: Chat) => this.handleBotResponse(response),
      error: (err) => {
        this.setErrorMessage();
      }
    })
  }

  setErrorMessage() {
    this.clearTimeoutForLoaderText();
    this.leftContainerClass = 'left-side-container-error';
    this.loaderText = 'Oops something went wrong , please try again.';
    this.rightContainerClass = 'right-side-container-error';
    this.showLoaderLikeDislikeButtons = false;
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
    if (this.loaderTextIndex == 3) {
      this.loaderTextIndex = 0;
    }
    this.leftContainerClass = 'left-side-container-' + (this.loaderTextIndex + 1);
    this.rightContainerClass = 'right-side-container-' + (this.loaderTextIndex + 1);
    this.loaderTextIndex++;
  }

  setTimeoutForLoaderText() {
    this.loaderText = this.loaderTextArray[Math.round(Math.random() * 10)];
    this.showLoaderLikeDislikeButtons = false;
    this.loaderTextTimeout = setInterval(() => { this.setCyclicLoaderText(); }, 3000);
  }

  clearTimeoutForLoaderText() {
    clearTimeout(this.loaderTextTimeout);
  }

  setCyclicLoaderText() {
    this.loaderText = this.loaderTextArray[Math.round(Math.random() * 10)];
    this.loaderIndex++;
  }

  handleBotResponse(response: Chat) {
    let endTime = new Date().getTime();
    this.assignId(response?.id);

    // --- Store the chat ID after the FIRST successful response ---
    if (!this.currentChatId && response.id) {
      this.currentChatId = response.id;
      console.log("Stored Chat ID:", this.currentChatId); // For debugging
    }

    let singleMesage: Message = {
      body: "",
      botAnswer: response.answer,
      type: 'bot',
      responseTime: ((endTime - this.botStartTime) / 1000).toString(),
      shareable: true,
      categoryIntent: response.intent,
      botStartTime: this.botStartTime.toString(),
      extras: {
        like: false,
        dislike: false,
        delete: false,
      },
      chat_id: response.id
    };

    this.conversation.unshift(singleMesage);
    this.setSuggestedQuestionInChat(response, endTime);
    this.showLoader = false;
    this.clearTimeoutForLoaderText();
    this.isSuggestedQuestion = '';
  }

  // adds Suggested question as another message
  setSuggestedQuestionInChat(response: Chat, endTime: number) {
    if (response.suggested_questions?.length || 0 > 0) {
      this.showSuggesstion = true;
      this.suggestedQuestionMessage = {
        body: "",
        type: 'bot',
        responseTime: ((endTime - this.botStartTime) / 1000).toString(),
        shareable: true,
        categoryIntent: response.intent,
        extras: {
          like: false,
          dislike: false
        },
        suggestedQuestion: response.suggested_questions
      }
      setTimeout(() => {
        const botResponseElement = document.getElementById(this.botStartTime.toString());
        const parentElement = document.getElementsByClassName('chat-body');
        const y = botResponseElement?.offsetTop;
        if (y) {
          parentElement[0].scroll({
            top: y - 30,
            behavior: 'smooth'
          })
        }
      }, 1000);
    }
  }

  chipControlOnSelect(event: any) {
    this.chatQuery = event.target.innerText;
    this.submitMessage(event);
  }

  getResponseforSuggestionQuery(event: any) {
    this.isSuggestedQuestion = event;
    this.chatQuery = event;
    document.querySelectorAll(".bot-suggestion-container").forEach(el => el.remove());
    this.submitMessage(event);
  }

  removeSuggestionElement() {
    this.showSuggesstion = false;
    document.querySelectorAll(".bot-suggestion-container").forEach(el => el.remove());
  }

  resetBrowser() {
    this.currentChatId = null;
    this.sessionService.createSession();
    this.router.navigateByUrl('/');
  }


  openSnackBar(message: string, color: string) {
    this._snackBar.open(message, 'Close', {
      panelClass: [color],
      horizontalPosition: 'end',
      verticalPosition: 'top',
      duration: 3000,
    });
  }

  startRecording() {
    this.isRecording = true;
    this.audioChunks = [];
    this.mediaRecorder.start();
  }

  stopRecording() {
    this.isRecording = false;
    this.mediaRecorder.stop();
  }

}
