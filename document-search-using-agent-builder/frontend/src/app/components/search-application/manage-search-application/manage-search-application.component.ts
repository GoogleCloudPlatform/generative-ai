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
import {SearchApplicationService} from 'src/app/services/search_application.service';
import {ReplaySubject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';
import {UserService} from 'src/app/services/user/user.service';
import {Router} from '@angular/router';
import {Engine} from 'src/app/models/engine.model';
import {EnginesService} from 'src/app/services/engines.service';

@Component({
  selector: 'app-manage-search-application',
  templateUrl: './manage-search-application.component.html',
  styleUrls: ['./manage-search-application.component.scss'],
})
export class ManageSearchApplicationComponent implements OnDestroy {
  selectedEngine: Engine | undefined;
  engines: Engine[] = [];
  editMode = false;
  savedEngineID = '';
  private readonly destroyed = new ReplaySubject<void>(1);

  constructor(
    private readonly searchApplicationService: SearchApplicationService,
    private readonly userService: UserService,
    private readonly router: Router,
    private enginesService: EnginesService
  ) {
    this.enginesService
      .getAll()
      .subscribe(response => (this.engines = response));
    this.disableForm();
    this.getConfigData();
  }

  disableForm() {
    this.editMode = false;
  }

  enableForm() {
    this.editMode = true;
  }

  getConfigData() {
    this.userService.showLoading();
    this.searchApplicationService
      .get()
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: response => {
          this.savedEngineID = response.engine_id;
          this.selectedEngine = this.engines.filter(
            e => e.engine_id === response.engine_id
          )[0];
          this.userService.hideLoading();
        },
        error: () => {
          this.userService.hideLoading();
        },
      });
  }

  saveForm() {
    this.userService.showLoading();
    const searchApplication = {
      engine_id: this.selectedEngine?.engine_id || "",
      region: this.selectedEngine?.region || "",
    };

    this.searchApplicationService
      .update(this.savedEngineID, searchApplication)
      .subscribe({
        next: () => {
          this.savedEngineID = this.selectedEngine?.engine_id || "";
          this.userService.hideLoading();
          this.disableForm();
        },
        error: () => {
          this.userService.hideLoading();
        },
      });
  }

  navigateToMain() {
    this.router.navigateByUrl('/');
  }

  ngOnDestroy(): void {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
