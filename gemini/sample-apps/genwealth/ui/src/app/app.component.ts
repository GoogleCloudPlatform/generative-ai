import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { RouterModule } from '@angular/router';
import { BreakpointObserver, Breakpoints} from '@angular/cdk/layout';

import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';

import { InvestmentsComponent } from './investments/investments.component';
import { ProspectsComponent } from './prospects/prospects.component';
import { ChatComponent } from './chat/chat.component';
import { SnackBarErrorComponent } from './common/SnackBarErrorComponent';


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    RouterOutlet, 
    RouterModule,
    MatButtonModule,
    MatToolbarModule,
    MatIconModule,
    InvestmentsComponent,
    ProspectsComponent,
    ChatComponent,
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
  providers: [SnackBarErrorComponent]
})
export class AppComponent implements OnInit {
  constructor(private breakpointObserver: BreakpointObserver) {}

  isSmallScreen: boolean = false;

  ngOnInit() { 
    this.breakpointObserver
      .observe([Breakpoints.Handset])
      .subscribe( _ => this.isSmallScreen = this.breakpointObserver.isMatched(Breakpoints.Handset) );
  }
}
