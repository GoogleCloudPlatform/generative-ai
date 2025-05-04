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
import {SearchApplicationFormComponent} from '../search-application/search-application-form/search-application-form.component';
import {ReplaySubject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';
import {SearchResponse} from 'src/app/models/search.model';
import {SearchApplicationService} from 'src/app/services/search_application.service';

@Component({
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent implements OnDestroy {
  private readonly destroyed = new ReplaySubject<void>(1);
  term = '';
  showResults = false;
  searchResults: SearchResponse;
  savedUser;

  constructor(
    public userService: UserService,
    private router: Router,
    public dialog: MatDialog,
    private readonly searchApplicationService: SearchApplicationService
  ) {
    this.savedUser = userService.getUserDetails();
    this.checkConfiguration();
  }

  checkConfiguration() {
    this.searchApplicationService
      .get()
      .pipe(takeUntil(this.destroyed))
      .subscribe(searchApplication => {
        if (!searchApplication) {
          this.openAddAgentBuilderConfigForm();
        }
      });
  }

  goToResults(term: string) {
    this.router.navigate(['/search'], {queryParams: {q: term}});
  }

  openAddAgentBuilderConfigForm() {
    this.dialog.open(SearchApplicationFormComponent, {
      disableClose: true,
      height: '600px',
      width: '1120px',
    });
  }

  ngOnDestroy() {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
