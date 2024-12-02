import { Component, Input, Output, EventEmitter } from '@angular/core';
import { SuggestionData } from 'src/app/models/messegeType.model';
@Component({
  selector: 'app-suggestion-card',
  templateUrl: './suggestion-card.component.html',
  styleUrls: ['./suggestion-card.component.scss']
})
export class SuggestionCardComponent {
  @Input() data: SuggestionData;
  @Output() raiseQuery = new EventEmitter<string>();
  @Output() dismissSuggestionCard = new EventEmitter();


  assignQToChatQuery(question: string){
    this.raiseQuery.emit(question);
  }

  closeSuggestionCard(){
    this.dismissSuggestionCard.emit();
  }
}
