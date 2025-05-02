import {Component, OnDestroy} from '@angular/core';
import {UserService} from 'src/app/services/user/user.service';
import {Router} from '@angular/router';
import {MatDialog} from '@angular/material/dialog';
import {ReplaySubject} from 'rxjs';
import {SearchResponse} from 'src/app/models/search.model';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent implements OnDestroy {
  private readonly destroyed = new ReplaySubject<void>(1);
  term = '';
  showResults = false;
  searchResults: SearchResponse = {
    summary: undefined,
    results: [],
    totalSize: 0,
  };
  savedUser;

  constructor(
    public userService: UserService,
    private router: Router,
    public dialog: MatDialog
  ) {
    this.savedUser = userService.getUserDetails();
  }

  goToResults(file: File) {
    this.router.navigate(['/search'], {
      queryParams: {
        q: "Change the background by adding a beautiful, sprawling city with skyscrapers to this professional and elegant LinkedIn profile picture. It's dusk, and you can still see the sun before it sets.",
        filename: file.name,
      },
    });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
