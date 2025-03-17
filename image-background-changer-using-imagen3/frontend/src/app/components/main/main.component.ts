import {Component, OnDestroy, ViewChild, TemplateRef} from '@angular/core';
import {UserService} from 'src/app/services/user/user.service';
import {Router} from '@angular/router';
import {MatDialog} from '@angular/material/dialog';
import {ReplaySubject} from 'rxjs';
import {SearchResponse} from 'src/app/models/search.model';
import {ImageService} from 'src/app/services/image/image.service';
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
    public dialog: MatDialog,
    private imageService: ImageService
  ) {
    this.savedUser = userService.getUserDetails();
  }

  goToResults(file: File) {
    this.imageService.setImage(file); // Store the file in the service
    this.router.navigate(['/search'], {
      queryParams: {q: 'Generate a nice light wood countertop background for this product image', filename: file.name},
    });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
