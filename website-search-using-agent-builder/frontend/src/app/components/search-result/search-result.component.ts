import { Component } from '@angular/core';
import { ActivatedRoute} from '@angular/router';
@Component({
  selector: 'app-search-result',
  templateUrl: './search-result.component.html',
  styleUrls: ['./search-result.component.scss']
})
export class SearchResultComponent {
  query : string = '';
  constructor(private readonly route: ActivatedRoute){
    this.route.paramMap.subscribe((param:any)=>{
      this.query = param.get('query');
    });
  }

}
