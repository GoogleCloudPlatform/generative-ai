import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from 'src/environments/environment';
import { map } from 'rxjs/operators';
import { config } from '../models/config.model';
import {Observable} from 'rxjs';

const configURL = `${environment.backendURL}/agent-configs`;

@Injectable({
  providedIn: 'root'
})
export class ConfigurationService {

  constructor(private readonly http: HttpClient) { }

  getConfiguration(): Observable<config[]>{
      return this.http.get(configURL).pipe(map(response=> response as config[]));
  }

  addConfiguration(agentBuilderUrl: string){
    return this.http.post(configURL, {name:environment.chatbotName , url: agentBuilderUrl});
  }

  updateConfig(agentBuilderUrl: string){
    return this.http.put(`${configURL}/${environment.chatbotName}`, {name: environment.chatbotName, url: agentBuilderUrl});
  }

  deleteConfiguration(){
    return this.http.delete(`${configURL}/${environment.chatbotName}`);
  }
}
