import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Observable } from 'rxjs';

import { Prospect, QueryResponse } from '../../services/genwealth-api';
import { TextToHtmlPipe } from '../../common/text-to-html.pipe';
import { SqlStatementComponent } from '../../common/sql-statement/sql-statement.component';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';

@Component({
  selector: 'app-prospect-results',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTableModule, 
    MatButtonModule, 
    SqlStatementComponent,
    MatIconModule,
    TextToHtmlPipe,
  ],
  templateUrl: './prospect-results.component.html',
  styleUrl: './prospect-results.component.scss',
  animations: [
    trigger('detailExpand', [
      state('collapsed,void', style({height: '0px', minHeight: '0'})),
      state('expanded', style({height: '*'})),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],  
})
export class ProspectResultsComponent implements OnInit {
  constructor(private breakpointObserver: BreakpointObserver) {}

  @Input()
  set prospects(observable: Observable<QueryResponse<Prospect>>) {
    observable.subscribe({ next: response => {
      if (response.data)
        this.dataSource.data = response.data; 
      this.query = response.query;
    }});
  }

  columnsToDisplaySmall: string[] = ['id', 'firstName','lastName'];
  columnsToDisplayLarge: string[] =[...this.columnsToDisplaySmall, 'email','age','riskProfile'];
  columnsToDisplay: string[] = this.columnsToDisplayLarge;
  columnsToDisplayWithExpand: string[] = [];
  expandedElement?: Prospect | null;  
  dataSource = new MatTableDataSource<Prospect>();
  query?: string = undefined;

  ngOnInit() { 
    this.breakpointObserver
      .observe([Breakpoints.Handset])
      .subscribe(_ => {
        if (this.breakpointObserver.isMatched(Breakpoints.Handset)) {
          console.log('Handset');
          this.columnsToDisplay = this.columnsToDisplaySmall;
        } else {
          console.log('Big');
          this.columnsToDisplay = this.columnsToDisplayLarge;
        }
        this.columnsToDisplayWithExpand = [...this.columnsToDisplay, 'expand'];
      });
  }
}
