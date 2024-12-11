import { Component } from '@angular/core';
import { UserService } from 'src/app/services/user/user.service';
import { SearchService } from 'src/app/services/search.service';
import { SearchResponse } from 'src/app/models/search.model';
import { Router } from '@angular/router';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent {
  term: string = '';
  showResults: boolean = false;
  searchResults: SearchResponse
  savedUser;
  chatQuery: string = '';

  constructor(
    private service: SearchService,
    public userService: UserService,
    private router: Router,
  ) {
    this.savedUser = userService.getUserDetails();
  }

  navigate() {
    if(this.chatQuery) this.service.nextChatQuery(this.chatQuery);
    this.router.navigateByUrl('/result');
  };


}
