import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QueryResponse, Investment } from '../../services/genwealth-api';
import { Observable } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';

import { TextToHtmlPipe } from '../../common/text-to-html.pipe';
import { SqlStatementComponent } from '../../common/sql-statement/sql-statement.component';

@Component({
  selector: 'app-investment-results',
  standalone: true,
  imports: [
    CommonModule, 
    MatCardModule,
    MatExpansionModule,
    SqlStatementComponent,
    TextToHtmlPipe,
  ],
  templateUrl: './investment-results.component.html',
  styleUrl: './investment-results.component.scss'
})
export class InvestmentResultsComponent {
  @Input()
  set investments(observable: Observable<QueryResponse<Investment>> | undefined) {
    if (!observable)
      return;
    
    observable.subscribe(response => {
      this.query = response.query;
      this.data = response.data;
    });
  }

  query?: string = undefined;
  data?: Investment[] = undefined;
}
