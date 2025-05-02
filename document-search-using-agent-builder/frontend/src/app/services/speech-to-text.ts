import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {environment} from 'src/environments/environment';

const audioChatUrl = `${environment.backendURL}/audio_chat`;

@Injectable({
  providedIn: 'root',
})
export class SpeechToTextService {
  constructor(private http: HttpClient) {}

  async transcribeAudio(audioBlob: Blob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'audio.wav');
    return this.http.post(audioChatUrl, formData);
  }
}
