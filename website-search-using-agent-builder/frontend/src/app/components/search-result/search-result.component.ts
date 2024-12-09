import { Component } from '@angular/core';
import { ActivatedRoute} from '@angular/router';

interface searchResult {
  icon: string;
  title: string;
  description: string;
  metaData?: metaData;
}

interface metaData {
  index: string;
  creationDate: string;
  likes: number;
}

@Component({
  selector: 'app-search-result',
  templateUrl: './search-result.component.html',
  styleUrls: ['./search-result.component.scss']
})
export class SearchResultComponent {
  query : string = '';
  overView: string = 'Google Cloud Platform (GCP) is a suite of cloud computing services offered by Google. It provides a wide range of services, including computing, storage, databases, networking, analytics, machine learning, and more';
  serachResult : searchResult[] = [{
    icon: 'all_out',
    title: 'text titel for description',
    description: 'text title fpr description text title fpr description text title fpr descriptiontext title fpr descriptiontext title fpr descriptiontext title fpr description'
  },
  {
    icon: 'all_out',
    title: 'text titel for description',
    description: 'text title fpr description text title fpr description text title fpr descriptiontext title fpr descriptiontext title fpr descriptiontext title fpr description'
  }
];
  
  constructor(private readonly route: ActivatedRoute){
    this.route.paramMap.subscribe((param:any)=>{
      this.query = param.get('query');
    });
  }


}
