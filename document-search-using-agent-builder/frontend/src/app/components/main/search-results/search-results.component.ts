import { Component, OnDestroy } from '@angular/core';
import { SearchService } from 'src/app/services/search.service';
import {ReplaySubject} from 'rxjs';
import { UserService } from 'src/app/services/user/user.service';
import { ActivatedRoute, Router } from '@angular/router';
import { search_document_type, search_image_type, PDF, image_name } from 'src/environments/constant';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent implements OnDestroy {
  summary: string = '';
  private readonly destroyed = new ReplaySubject<void>(1);
  serachResult : any = [];
  documents : any = [];
  images : any = [];
  pdf = PDF;
  imageName = image_name;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private service : SearchService,
    private userService: UserService,
  ){
    const query = this.route.snapshot.queryParamMap.get('q');

    this.service.search(query!).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone;
      searchRespone[3].link = 'text.jpeg'
      searchRespone.forEach((element: any) => {
        if(search_document_type.includes(element.link.split(".")[1])){
          this.documents.push(element);
        }
        if(search_image_type.includes(element.link.split(".")[1])){
          this.images.push(element);
        }
      });
      console.log(this.documents, this.images);
      this.userService.hideLoading();
      },
      error : ()=>{
        this.userService.hideLoading();
      }
    });
  }

  searchTerm(term: string) {
    this.router.navigate(['/search'], { queryParams: { q: term }});

    this.service.search(term).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone;
      this.userService.hideLoading();
      },
      error : ()=>{
        this.userService.hideLoading();
      }
    });
  }

  openNewWindow(link: string) {
    window.open(link, "_blank")
  }

  ngOnDestroy(){
    this.destroyed.next();
    this.destroyed.complete();
  }
}
