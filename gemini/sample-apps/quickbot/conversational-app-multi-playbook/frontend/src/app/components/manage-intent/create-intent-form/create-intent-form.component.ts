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

import {Component, EventEmitter, Input, Output} from '@angular/core';
import {FormArray, FormControl, FormGroup, Validators} from '@angular/forms';
import {
  IntentDetails,
  IntentService,
  Model,
} from 'src/app/services/intent.service';
import {ToastMessageComponent} from '../../shared/toast-message/toast-message.component';
import {MatSnackBar} from '@angular/material/snack-bar';

@Component({
  selector: 'app-create-intent-form',
  templateUrl: './create-intent-form.component.html',
  styleUrls: ['./create-intent-form.component.scss'],
})
export class CreateIntentFormComponent {
  @Input() models: Model[];
  @Output() discardFormCreation: EventEmitter<boolean> = new EventEmitter();

  hasExternalDataSource = false;
  showSpinner = false;

  intentForm = new FormGroup({
    name: new FormControl<string>('', Validators.required),
    gcp_bucket: new FormControl<string>(''),
    description: new FormControl<string>('', Validators.required),
    prompt: new FormControl<string>('', Validators.required),
    ai_model: new FormControl<string>('', Validators.required),
    ai_temperature: new FormControl<string>('', Validators.required),
    questions: new FormArray<FormControl<string | null>>([
      new FormControl<string>(
        {value: '', disabled: false},
        Validators.required
      ),
    ]),
  });

  constructor(
    private snackbar: MatSnackBar,
    private service: IntentService
  ) {}

  toggleHasExternalDataSource() {
    this.hasExternalDataSource = !this.hasExternalDataSource;
  }

  removeQuestion(i: number) {
    this.intentForm.controls.questions.removeAt(i);
  }

  addQuestion() {
    this.intentForm.controls.questions.push(
      new FormControl<string>({value: '', disabled: false}, Validators.required)
    );
  }

  discardForm() {
    this.discardFormCreation.emit();
  }

  saveForm() {
    if (
      !this.intentForm.valid ||
      !this.intentForm.controls.questions.valid ||
      (this.hasExternalDataSource &&
        this.intentForm.controls.gcp_bucket.value === '')
    ) {
      this.snackbar.openFromComponent(ToastMessageComponent, {
        panelClass: ['red-toast'],
        verticalPosition: 'top',
        horizontalPosition: 'right',
        duration: 5000,
        data: {
          text: 'There is an error on the intent creation form',
          icon: 'cross-in-circle-white',
        },
      });
      return;
    }

    this.showSpinner = true;
    const intent: IntentDetails = {
      name: this.intentForm.controls.name.value!,
      gcp_bucket: this.intentForm.controls.gcp_bucket.value!,
      description: this.intentForm.controls.description.value!,
      prompt: this.intentForm.controls.prompt.value!,
      ai_model: this.intentForm.controls.ai_model.value!,
      ai_temperature: this.intentForm.controls.ai_temperature.value!,
      questions: this.intentForm.controls.questions.value as string[],
      status: '1',
    };

    this.service.saveIntent(intent).subscribe({
      next: () => {
        this.showSpinner = false;
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['green-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: 'Intent Saved', icon: 'tick-with-circle'},
        });
        window.location.reload();
      },
      error: response => {
        const message =
          response.error && response.error.detail
            ? response.error.detail
            : 'Error creating intent';
        this.showSpinner = false;
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['red-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: message, icon: 'cross-in-circle-white'},
        });
      },
    });
  }
}
