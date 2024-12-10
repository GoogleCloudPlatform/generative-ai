import { Component, Input } from '@angular/core';
import { SearchResponse } from 'src/app/models/search.model';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent {
  summary: string = '';
  @Input() searchResults: SearchResponse

  navigateToLink(link: string) {
    window.open(link, "_blank")
  }
}
