/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {Component, OnDestroy} from '@angular/core';
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
      queryParams: {
        q: 'Change the background to be minimalist, elegant, with a soft neutral color palette and subtle shadows, conveying a sense of sophistication and high quality.',
        filename: file.name,
      },
    });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
