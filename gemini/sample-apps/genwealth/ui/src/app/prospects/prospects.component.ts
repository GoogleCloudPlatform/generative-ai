import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GenWealthServiceClient, Prospect, QueryResponse } from '../services/genwealth-api';
import { Observable, catchError } from 'rxjs';

import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatSliderModule } from '@angular/material/slider';
import { MatSlideToggleChange, MatSlideToggleModule } from '@angular/material/slide-toggle';

import { ProspectResultsComponent } from './results/prospect-results.component';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { SnackBarErrorComponent } from '../common/SnackBarErrorComponent';

@Component({
  selector: 'app-prospects',
  standalone: true,
  imports: [
    CommonModule, 
    MatButtonModule,
    FormsModule,
    MatInputModule,
    MatCardModule,
    MatSliderModule,
    MatSlideToggleModule,
    MatIconModule,
    MatTooltipModule,    
    ProspectResultsComponent,
  ],
  templateUrl: './prospects.component.html',
  styleUrl: './prospects.component.scss'
})
export class ProspectsComponent {
  constructor(
    private genWealthClient: GenWealthServiceClient,
    private error: SnackBarErrorComponent) {}

  prospectSearch: string = '';
  useFilters: boolean = false;
  minAge: number = 21;
  maxAge: number = 65;
  riskProfile: number = 1;

  prospects?: Observable<QueryResponse<Prospect>> = undefined;

  useFiltersChange(change: MatSlideToggleChange) {
    this.useFilters = change.checked;
  }

  formatRiskLabel(value: number): string {
    switch (value) {
      case 1:
        return 'low';
      case 2:
        return 'medium';
      case 3:
        return 'high';
      default:
        return '';
    }
  }

  findProspects() {
    let riskFilter: string | undefined = this.useFilters ? 
      this.formatRiskLabel(this.riskProfile) : undefined;
    
    let minAgeFilter: number | undefined = this.useFilters ?
      this.minAge : undefined;

    let maxAgeFilter: number | undefined = this.useFilters ?
      this.maxAge : undefined;      

    console.log('finding...', this.prospectSearch, riskFilter, minAgeFilter, maxAgeFilter);

    this.prospects = 
      this.genWealthClient.semanticSearchProspects(this.prospectSearch,
        riskFilter, minAgeFilter, maxAgeFilter).pipe(
          catchError((err) => {
            this.error.showError('Unable to search investments', err);
            return [];
          })
        );
  }
}
