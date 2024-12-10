import { Component, OnDestroy } from '@angular/core';
import { ActivatedRoute} from '@angular/router';
import { BroadcastService } from 'src/app/services/broadcast.service';
import { ChatService } from 'src/app/services/chat.service';
import {ReplaySubject} from 'rxjs';
import {  takeUntil, switchMap
} from 'rxjs/operators';
import { UserService } from 'src/app/services/user/user.service';

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
export class SearchResultComponent implements OnDestroy {
  private readonly destroyed = new ReplaySubject<void>(1);
  query : string = '';
  overView: string = 'Google Cloud Platform (GCP) is a suite of cloud computing services offered by Google. It provides a wide range of services, including computing, storage, databases, networking, analytics, machine learning, and more';
  serachResult : any = [];
  
  constructor(private readonly route: ActivatedRoute, 
    private readonly chatService : ChatService, 
    private readonly broadcastService: BroadcastService,
    public userService: UserService,
    ){
    this.route.paramMap.subscribe((param:any)=>{
      this.query = param.get('query');
    });
    this.broadcastService.chatQuery$.pipe(takeUntil(this.destroyed), switchMap((query)=>{
      this.userService.showLoading();
      return this.chatService.postChat(query)
    })).subscribe({
      next : (searchRespone: any)=>{
      this.serachResult = searchRespone?.results;
      console.log(searchRespone, "searchRespone");
      this.userService.hideLoading();
    },
    error : ()=>{
      this.userService.hideLoading();
    }
  });
  }

  ngOnDestroy(){
    this.destroyed.next();
    this.destroyed.complete();
  }

  openNewWindow(link: string){
    window.open(link, '_blank');
  }


}
