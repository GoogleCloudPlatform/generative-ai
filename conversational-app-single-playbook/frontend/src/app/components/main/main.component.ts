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

import {IntentService, IntentDetails} from '../../services/intent.service';
import {Component, TemplateRef, ViewChild} from '@angular/core';
import {Router} from '@angular/router';
import {BroadcastService} from 'src/app/services/broadcast.service';
import {UntypedFormGroup, UntypedFormBuilder} from '@angular/forms';
import {UserService} from 'src/app/services/user/user.service';
import {Message} from 'src/app/models/messegeType.model';
import {SessionService} from 'src/app/services/user/session.service';
import {MatDialog} from '@angular/material/dialog';
import {ReplaySubject} from 'rxjs';
import {MatSnackBar} from '@angular/material/snack-bar';
import {
  animate,
  sequence,
  state,
  style,
  transition,
  trigger,
} from '@angular/animations';
import {SpeechToTextService} from '../../services/speech-to-text';
import {CreateIntentFormComponent} from '../manage-intent/create-intent-form/create-intent-form.component';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
  animations: [
    trigger('scale', [
      state('true', style({transform: 'translateY(0)', color: '#4285F4'})),
      transition('* => true', [
        sequence([
          style({transform: 'translateY(0)'}),
          animate(
            '450ms cubic-bezier(0,0,0,1)',
            style({transform: 'scale(0.8)', color: '#4285F4'})
          ),
          animate(
            '400ms cubic-bezier(1,0,1,1)',
            style({transform: 'scale(1.2)', color: '#4285F4'})
          ),
          animate(
            '350ms cubic-bezier(1,0,1,1)',
            style({transform: 'scale(0.8)', color: '#4285F4'})
          ),
          animate(
            '250ms cubic-bezier(0,0,0,1)',
            style({transform: 'scale(1)', color: '#4285F4'})
          ),
          animate(
            '200ms cubic-bezier(0,0,0,1)',
            style({transform: 'scale(-1,1)', color: '#4285F4'})
          ),
          animate(
            '150ms cubic-bezier(1,0,1,1)',
            style({transform: 'scale(-1,1)', color: '#4285F4'})
          ),
        ]),
      ]),
    ]),
  ],
})
export class MainComponent {
  isRecording = false;
  transcribedText = '';
  mediaRecorder: MediaRecorder | undefined;
  audioChunks: Blob[] = [];

  searchForm: UntypedFormGroup;
  selectedType = 'chat';
  chatQuery = '';
  chipSelected = '';
  allQuestions: Map<string, string[]> = new Map();
  onHover = false;
  savedUser;
  lastExpandedElement = '';
  showTos = false;
  showBadge = false;
  tooltipTextList: string[] = [];

  @ViewChild('userBadgeTemplate', {static: true})
  userBadgeTemplate!: TemplateRef<{}>;

  intentSelected = false;
  intents: IntentDetails[] = [];
  dialogRef: any;

  private readonly destroyed = new ReplaySubject<void>(1);
  toolTipText: string | undefined;
  tooltipTextTimeout: undefined | ReturnType<typeof setTimeout>;
  createIntentComponentInstance: any;

  constructor(
    private router: Router,
    private broadcastService: BroadcastService,
    private fb: UntypedFormBuilder,
    private sessionService: SessionService,
    public userService: UserService,
    private intentsService: IntentService,
    public dialog: MatDialog,
    private _snackBar: MatSnackBar,
    private speechToTextService: SpeechToTextService
  ) {
    this.intentsService.getAllIntent().subscribe(response => {
      if (response.length > 0) this.intents = response;
      else this.openCreateIntentForm();
    });
    this.searchForm = this.fb.group({
      searchTerm: this.fb.control(''),
    });
    this.savedUser = userService.getUserDetails();
    this.sessionService.createSession();
    this.setTimeoutForToolTipText();
  }

  openCreateIntentForm() {
    this.createIntentComponentInstance = this.dialog
      .open(CreateIntentFormComponent, {
        disableClose: true,
        height: '600px',
        width: '1120px',
      })
      .afterClosed()
      .subscribe(() => window.location.reload());
  }

  navigate() {
    const userMessage: Message = {
      body: this.chatQuery,
      type: 'user',
      shareable: false,
    };
    this.chatQuery && this.broadcastService.nextChatQuery(userMessage);
    this.router.navigateByUrl('/' + this.selectedType);
  }

  changeSelectedAssistance(assistantType: string) {
    this.selectedType = assistantType;
  }

  chipControlOnSelect(intent: IntentDetails) {
    const queryIntent = intent.name;
    this.chipSelected = queryIntent;
  }

  removeIntentSelection() {
    this.chipSelected = '';
  }

  assignQToChatQuery(question: string) {
    this.chatQuery = question;
    const userMessage: Message = {
      body: this.chatQuery,
      type: 'user',
      shareable: false,
    };
    this.chatQuery && this.broadcastService.nextChatQuery(userMessage);
    this.router.navigateByUrl('/' + this.selectedType);
  }

  showFullButton() {
    this.onHover = true;
  }
  hideFullButton() {
    this.onHover = false;
  }

  expandIntentContainer(intent: IntentDetails) {
    const classNameToFilterElement = intent.name;
    this.chipControlOnSelect(intent);
    if (this.lastExpandedElement !== '') {
      document
        .getElementsByClassName(this.lastExpandedElement)[0]
        ?.classList.add('intent-container-box');
      document
        .getElementsByClassName(this.lastExpandedElement)[0]
        ?.classList.remove('selected-intent-box');
      document
        .getElementsByClassName(
          this.lastExpandedElement + '_close_button_container'
        )[0]
        ?.classList.remove('expand-close-button-container');
      document
        .getElementsByClassName(
          this.lastExpandedElement + '_suggested_questions_container'
        )[0]
        ?.classList.remove('selected-intent-suggested-question');
    }
    if (this.lastExpandedElement === classNameToFilterElement) {
      document
        .getElementsByClassName(this.lastExpandedElement)[0]
        ?.classList.remove('selected-intent-box');
      document
        .getElementsByClassName(
          classNameToFilterElement + '_close_button_container'
        )[0]
        ?.classList.remove('expand-close-button-container');
      document
        .getElementsByClassName(
          this.lastExpandedElement + '_suggested_questions_container'
        )[0]
        ?.classList.remove('selected-intent-suggested-question');
      this.lastExpandedElement = '';
      return;
    }
    this.lastExpandedElement = classNameToFilterElement;
    const elementToExpand = document.getElementsByClassName(
      classNameToFilterElement
    );
    elementToExpand[0]?.classList.remove('intent-container-box');
    elementToExpand[0]?.classList.add('selected-intent-box');
    const suggestedQuestionElement = document.getElementsByClassName(
      classNameToFilterElement + '_suggested_questions_container'
    );
    suggestedQuestionElement[0]?.classList.add(
      'selected-intent-suggested-question'
    );
    const closeButtonElement = document.getElementsByClassName(
      classNameToFilterElement + '_close_button_container'
    );
    closeButtonElement[0]?.classList.add('expand-close-button-container');

    setTimeout(() => {
      this.scrollToSelectedElement(classNameToFilterElement);
    }, 100);

    return;
  }

  getHumanReadablestring(s: string) {
    return s
      .replace('_', ' ')
      .replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase());
  }

  scrollToSelectedElement(classNameToFilterElement: string) {
    const childElement = document.getElementById(classNameToFilterElement);
    childElement?.scrollIntoView();
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }

  openSnackBar(message: string, color: string) {
    this._snackBar.open(message, 'Close', {
      panelClass: [color],
      horizontalPosition: 'end',
      verticalPosition: 'top',
      duration: 3000,
    });
  }

  ngOnInit() {
    navigator.mediaDevices
      .getUserMedia({audio: true})
      .then(stream => this.setupMediaRecorder(stream));
  }

  setupMediaRecorder(stream: MediaStream) {
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = event =>
      this.audioChunks.push(event.data);
    this.mediaRecorder.onstop = () => this.sendAudioToGCP();
  }

  startRecording() {
    this.isRecording = true;
    this.audioChunks = [];
    if (this.mediaRecorder) this.mediaRecorder.start();
  }

  stopRecording() {
    this.isRecording = false;
    if (this.mediaRecorder) this.mediaRecorder.stop();
  }

  async sendAudioToGCP() {
    const audioBlob = new Blob(this.audioChunks);
    (await this.speechToTextService.transcribeAudio(audioBlob)).subscribe(
      (response: any) => {
        this.chatQuery = response[0];
      },
      (error: any) => console.error(error)
    );
  }

  setTimeoutForToolTipText() {
    if (!window.localStorage['showTooltip']) {
      this.toolTipText =
        this.tooltipTextList[
          Math.floor(Math.random() * this.tooltipTextList.length)
        ];
      this.tooltipTextTimeout = setInterval(() => {
        this.toolTipText =
          this.tooltipTextList[
            Math.floor(Math.random() * this.tooltipTextList.length)
          ];
      }, 7000);
    }
  }

  dismissToolTip() {
    window.localStorage['showTooltip'] = true;
    this.toolTipText = undefined;
    clearTimeout(this.tooltipTextTimeout);
  }
}
