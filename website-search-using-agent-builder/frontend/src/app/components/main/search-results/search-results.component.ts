import { Component, OnDestroy } from '@angular/core';
import { SearchService } from 'src/app/services/search.service';
import {ReplaySubject} from 'rxjs';
import { UserService } from 'src/app/services/user/user.service';
import {  takeUntil, switchMap
} from 'rxjs/operators';

@Component({
  selector: 'app-search-results',
  templateUrl: './search-results.component.html',
  styleUrls: ['./search-results.component.scss']
})
export class SearchResultsComponent implements OnDestroy {
  summary: string = '';
  private readonly destroyed = new ReplaySubject<void>(1);
  serachResult : any = [];

  constructor(private service : SearchService, private userService: UserService){
    this.service.chatQuery$.pipe(takeUntil(this.destroyed), switchMap((query)=>{
      this.userService.showLoading();
      return this.service.search(query)
    })).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone?.results;
      this.summary = searchRespone?.summary.text;
      console.log(searchRespone, "searchRespone");
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
