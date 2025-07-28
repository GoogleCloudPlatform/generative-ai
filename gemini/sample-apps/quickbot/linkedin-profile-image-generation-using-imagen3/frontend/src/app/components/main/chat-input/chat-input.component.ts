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

import {Component, EventEmitter, Output} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {SpeechToTextService} from 'src/app/services/speech-to-text';

@Component({
  selector: 'app-chat-input',
  templateUrl: './chat-input.component.html',
  styleUrls: ['./chat-input.component.scss'],
})
export class ChatInputComponent {
  isRecording = false;
  transcribedText = '';
  mediaRecorder: MediaRecorder | undefined;
  audioChunks: Blob[] = [];

  term = '';
  @Output() emitSearch: EventEmitter<string> = new EventEmitter();

  constructor(
    private speechToTextService: SpeechToTextService,
    private route: ActivatedRoute
  ) {
    const query = this.route.snapshot.queryParamMap.get('q');
    if (query) {
      this.term = query;
    }
  }

  ngOnInit() {
    navigator.mediaDevices
      .getUserMedia({audio: true})
      .then(stream => this.setupMediaRecorder(stream))
      .catch(err => {
        console.error(err);
      });
  }

  searchTerm() {
    this.emitSearch.emit(this.term);
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
        this.term = response[0];
        this.searchTerm();
      },
      (error: any) => {
        // Handle errors
        console.error('Error transcribing audio:', error);
      }
    );
  }
}
