import { Component } from '@angular/core';
import { UserService } from 'src/app/services/user/user.service';
import { SearchService } from 'src/app/services/search.service';
import { SearchResponse } from 'src/app/models/search.model';

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

  constructor(
    private service: SearchService,
    public userService: UserService,
  ) {
    this.savedUser = userService.getUserDetails();
  }

  searchTerm(term: string) {
    this.service.search(term).subscribe(response => {
      if (response) {
        this.showResults = true;
        this.searchResults = response
      }
    })
  };
}
