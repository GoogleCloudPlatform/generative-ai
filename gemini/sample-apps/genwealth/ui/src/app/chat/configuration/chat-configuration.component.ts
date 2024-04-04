import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ChatRequest } from '../../services/genwealth-api';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggle } from '@angular/material/slide-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatButtonModule } from '@angular/material/button';


@Component({
  selector: 'app-chat-configuration',
  standalone: true,
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,    
    MatSlideToggle,
    MatIconModule,
    MatTooltipModule,    
    FormsModule,
    MatButtonModule
  ],
  templateUrl: './chat-configuration.component.html',
  styleUrl: './chat-configuration.component.scss'
})
export class ChatConfigurationComponent {
  @Input()
  chatRequest?: ChatRequest;

  defaultRequest: ChatRequest = {
    prompt: '',
    advanced: true,
    useHistory: true,
    llmRole: 'You are a financial advisor named Paul',
    mission: 'Your mission is to provide a personalized response to this email, then offer to schedule a follow-up consultation.',
    outputInstructions: 'Begin your response with a professional greeting. Greet me by name if you know it. End your response with a signature that includes your name and GenWealth company affiliation.',
    responseRestrictions: 'You are not a licensed financial advisor, so your must never provide financial advice under any circumstance. Always start your response by warning that you are not authorized to provide financial advice. If you are asked for financial advice, politely decline to answer, and offer to help with financial education, account information, and basic information related to budgeting, saving, and types of investments.',
    disclaimer: 'LEGAL DISCLAIMER: All output from this chatbot is provided for informational purposes only. It is not intended to provide (and should not be relied on for) tax, investment, legal, accounting or financial advice. You should consult your own licensed tax, investment, legal and accounting advisors before engaging in any transaction.',
  }

  useDefault() {
    this.chatRequest = {
      ...this.defaultRequest, 
      prompt: this.chatRequest?.prompt ?? '',
      userId: this.chatRequest?.userId,
    };
  }

  reset() {
    const request = new ChatRequest(this.chatRequest?.prompt ?? '');
    request.userId = this.chatRequest?.userId;

    this.chatRequest = request;
  }
}
