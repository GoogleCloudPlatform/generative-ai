import {Component, EventEmitter, OnInit, Output} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {Observable, catchError, map} from 'rxjs';
import {AsyncPipe} from '@angular/common';
import {MatSelectModule} from '@angular/material/select';
import {MatInputModule} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import {GenWealthServiceClient} from '../../services/genwealth-api';
import { SnackBarErrorComponent } from '../SnackBarErrorComponent';

/**
 * @title Ticker symbol autocomplete
 */
@Component({
  selector: 'app-ticker-autocomplete',
  templateUrl: 'ticker-autocomplete.component.html',
  styleUrl: 'ticker-autocomplete.component.scss',
  standalone: true,
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    SnackBarErrorComponent,
    AsyncPipe,
  ],
})
export class TickerAutocompleteComponent {
  tickerControl = new FormControl('');
  tickers?: Observable<string[]>;

  constructor(
      private genWealthClient: GenWealthServiceClient, 
      private error: SnackBarErrorComponent) {
    this.tickers = this.genWealthClient.getTickers().pipe(
      // sort tickers alphabetically
      map((tickers) => tickers.sort()),
      catchError((err) => {
        this.error.showError('Unable to load tickers', err);
        return [];
      })
    )
  }

  @Output()
  tickerSelected = new EventEmitter<string>();

  onTickerSelected(ticker: string) {
    this.tickerSelected.emit(ticker);
  }
}
