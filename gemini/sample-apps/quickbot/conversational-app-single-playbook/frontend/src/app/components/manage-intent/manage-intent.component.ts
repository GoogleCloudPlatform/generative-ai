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
import {
  IntentService,
  IntentDetails,
  Model,
} from '../../services/intent.service';
import {ModelsService} from 'src/app/services/models.service';

@Component({
  selector: 'app-manage-intent',
  templateUrl: './manage-intent.component.html',
  styleUrls: ['./manage-intent.component.scss'],
})
export class ManageIntentComponent {
  intents: IntentDetails[];
  showMainSpinner = false;
  models: Model[] = [];
  createMode = false;

  constructor(
    private intentService: IntentService,
    private modelsService: ModelsService
  ) {
    this.getAllIntent();
    this.modelsService.getAll().subscribe(response => {
      this.models = response;
    });
  }

  getAllIntent() {
    this.showMainSpinner = true;
    this.intentService.getAllIntent().subscribe({
      next: response => {
        this.showMainSpinner = false;
        this.intents = response;
      },
      error: () => {
        this.showMainSpinner = false;
        console.log('error');
      },
    });
  }

  enterCreateMode() {
    this.createMode = true;
  }

  exitCreateMode() {
    this.createMode = false;
  }
}
