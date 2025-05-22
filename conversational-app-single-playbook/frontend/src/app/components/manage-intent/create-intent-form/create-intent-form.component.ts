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

import {Component, EventEmitter, Output} from '@angular/core';
import {FormArray, FormControl, FormGroup, Validators} from '@angular/forms';
import {
  IntentDetails,
  IntentService,
  Model,
} from 'src/app/services/intent.service';
import {ToastMessageComponent} from '../../shared/toast-message/toast-message.component';
import {MatSnackBar} from '@angular/material/snack-bar';
import {MatDialogRef} from '@angular/material/dialog';
import {Router} from '@angular/router';
import {ModelsService} from 'src/app/services/models.service';

@Component({
  selector: 'app-create-intent-form',
  templateUrl: './create-intent-form.component.html',
  styleUrls: ['./create-intent-form.component.scss'],
})
export class CreateIntentFormComponent {
  @Output() discardFormCreation: EventEmitter<boolean> = new EventEmitter();

  models: Model[] = [];
  showSpinner = false;

  intentForm = new FormGroup({
    name: new FormControl<string>('', Validators.required),
    gcp_bucket: new FormControl<string>(''),
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
    private service: IntentService,
    private readonly dialogRef: MatDialogRef<CreateIntentFormComponent>,
    private readonly router: Router,
    private readonly modelsService: ModelsService
  ) {
    this.modelsService.getAll().subscribe(response => {
      this.models = response;
    });
  }

  discardForm() {
    this.discardFormCreation.emit();
  }

  removeQuestion(i: number) {
    this.intentForm.controls.questions.removeAt(i);
  }
  addQuestion() {
    this.intentForm.controls.questions.push(
      new FormControl<string>({value: '', disabled: false}, Validators.required)
    );
  }

  saveForm() {
    if (
      !this.intentForm.valid ||
      !this.intentForm.controls.questions.valid ||
      this.intentForm.controls.gcp_bucket.value === ''
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

    const intent: IntentDetails = {
      name: this.intentForm.controls.name.value!,
      gcp_bucket: this.intentForm.controls.gcp_bucket.value!,
      prompt: this.intentForm.controls.prompt.value!,
      ai_model: this.intentForm.controls.ai_model.value!,
      ai_temperature: this.intentForm.controls.ai_temperature.value!,
      questions: this.intentForm.controls.questions.value as string[],
      status: '1',
    };
    this.showSpinner = true;
    this.service.saveIntent(intent).subscribe({
      next: () => {
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['green-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: 'Intent Saved', icon: 'tick-with-circle'},
        });
        this.showSpinner = false;
        this.dialogRef.close()!;
        this.router.navigateByUrl('/');
        this.dialogRef.close();
      },
      error: response => {
        this.showSpinner = false;
        const message =
          response.error && response.error.detail
            ? response.error.detail
            : 'Error creating intent';
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
