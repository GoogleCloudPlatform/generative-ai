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

import {Component} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';
import {Router} from '@angular/router';
import {Engine} from 'src/app/models/engine.model';
import {EnginesService} from 'src/app/services/engines.service';
import {SearchApplicationService} from 'src/app/services/search_application.service';
import {UserService} from 'src/app/services/user/user.service';

@Component({
  selector: 'app-search-application-form',
  templateUrl: './search-application-form.component.html',
  styleUrls: ['./search-application-form.component.scss'],
})
export class SearchApplicationFormComponent {
  showSpinner = false;
  selectedEngine: Engine;
  engines: Engine[] = [];

  constructor(
    private dialogRef: MatDialogRef<SearchApplicationFormComponent>,
    private readonly router: Router,
    private readonly searchApplicationService: SearchApplicationService,
    private userService: UserService,
    private enginesService: EnginesService
  ) {
    this.enginesService
      .getAll()
      .subscribe(response => (this.engines = response));
  }

  saveForm() {
    if (this.selectedEngine) {
      const searchApplication = {
        engine_id: this.selectedEngine.engine_id,
        region: this.selectedEngine.region,
      };
      this.userService.showLoading();
      this.searchApplicationService.create(searchApplication).subscribe({
        next: () => {
          this.userService.hideLoading();
          this.dialogRef.close()!;
          this.router.navigateByUrl('/');
        },
        error: () => {
          this.userService.hideLoading();
        },
      });
    }
  }
}
