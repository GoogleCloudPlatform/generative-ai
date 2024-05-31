import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ChatRequest, ChatResponse, GenWealthServiceClient } from '../services/genwealth-api';
import { TextToHtmlPipe } from '../common/text-to-html.pipe';

import { MatButtonModule } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSlideToggle } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ChatConfigurationComponent } from './configuration/chat-configuration.component';
import { SqlStatementComponent } from '../common/sql-statement/sql-statement.component';
import { ActivatedRoute } from '@angular/router';
import { SnackBarErrorComponent } from '../common/SnackBarErrorComponent';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    FormsModule,
    MatInputModule,    
    MatSlideToggle,
    MatSidenavModule,
    MatCardModule,
    MatProgressSpinnerModule,
    TextToHtmlPipe,
    SqlStatementComponent,
    MatIconModule,
    MatTooltipModule,
    ChatConfigurationComponent,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit { 
  chatPlaceholder = "Ask me a question";
  loading: boolean = false;
  chatRequest: ChatRequest = new ChatRequest("");
  chatResponse?: ChatResponse = undefined;
  
  constructor(
    private cdRef: ChangeDetectorRef,
    private route: ActivatedRoute,
    private error: SnackBarErrorComponent,
    private genWealthClient: GenWealthServiceClient) {}  

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const userId = params.get('userId') ?? undefined;
      this.chatRequest.userId = userId ? Number(userId) : undefined;
    });
  }

  askQuestion() { 
    this.cdRef.detectChanges();
    this.loading = true;
    this.genWealthClient.chat(this.chatRequest)
      .subscribe({ 
        next: response => {
          this.chatResponse = response;
          this.loading = false;
        },
        error: err => {
          this.error.showError('Error connecting to chat server', err);
          this.loading = false;
        },
      });
  }

  getAskSuggestion() {
    this.chatRequest.prompt = 'Hi Paul,\n\nI just unexpectedly inherited about $10k, and I’m not sure how I should invest it. What do you recommend? \n\nThanks,\nDonya Bartle';
  }
}
