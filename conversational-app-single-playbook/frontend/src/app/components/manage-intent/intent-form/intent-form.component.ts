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

import {
  Component,
  Input,
  OnChanges,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import {FormArray, FormControl, FormGroup, Validators} from '@angular/forms';
import {MatSnackBar} from '@angular/material/snack-bar';
import {
  IntentDetails,
  IntentService,
  Model,
} from 'src/app/services/intent.service';
import {ToastMessageComponent} from '../../shared/toast-message/toast-message.component';
import {MatDialog, MatDialogRef} from '@angular/material/dialog';
import {Router} from '@angular/router';

@Component({
  selector: 'app-intent-form',
  templateUrl: './intent-form.component.html',
  styleUrls: ['./intent-form.component.scss'],
})
export class IntentFormComponent implements OnChanges {
  @Input() models: Model[] = [];
  @Input() intent: IntentDetails = {
    name: '',
    ai_model: '',
    ai_temperature: '',
    prompt: '',
    status: '',
    questions: [],
  };

  editMode = false;
  showSpinner = false;

  @ViewChild('deleteDialogRef', {static: true})
  deleteDialogRef!: TemplateRef<{}>;
  deleteIntentDialogRef?: MatDialogRef<{}>;

  intentForm = new FormGroup({
    name: new FormControl<string>('', Validators.required),
    gcp_bucket: new FormControl<string>('', Validators.required),
    prompt: new FormControl<string>('', Validators.required),
    ai_model: new FormControl<string>('', Validators.required),
    ai_temperature: new FormControl<string>('', Validators.required),
    questions: new FormArray<FormControl<string | null>>([]),
  });

  constructor(
    private dialog: MatDialog,
    private service: IntentService,
    private snackbar: MatSnackBar,
    private router: Router
  ) {
    this.intentForm.disable();
  }

  ngOnChanges(): void {
    this.intentForm.controls.name.setValue(this.intent.name);
    this.intentForm.controls.gcp_bucket.setValue(this.intent.gcp_bucket || '');
    this.intentForm.controls.prompt.setValue(this.intent.prompt);
    this.intentForm.controls.ai_model.setValue(this.intent.ai_model);
    this.intentForm.controls.ai_temperature.setValue(
      this.intent.ai_temperature
    );
    this.intentForm.controls.questions = new FormArray<
      FormControl<string | null>
    >([]);
    for (const question of this.intent.questions) {
      this.intentForm.controls.questions.push(
        new FormControl<string>(
          {value: question, disabled: true},
          Validators.required
        )
      );
    }
  }

  getHumanReadablestring(s: string) {
    return s
      .replace('_', ' ')
      .replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase());
  }

  toggleEditMode() {
    this.editMode = !this.editMode;
    if (this.editMode) {
      this.intentForm.enable();
      this.intentForm.controls.questions.enable();
      this.intentForm.controls.name.disable();
      this.intentForm.controls.gcp_bucket.disable();
    } else {
      this.intentForm.disable();
      this.intentForm.controls.questions.disable();
    }
  }

  removeQuestion(i: number) {
    this.intentForm.controls.questions.removeAt(i);
  }

  addQuestion() {
    this.intentForm.controls.questions.push(
      new FormControl<string>({value: '', disabled: false}, Validators.required)
    );
  }

  showDeleteDialog(event: any) {
    event.stopPropagation();
    this.deleteIntentDialogRef = this.dialog.open(this.deleteDialogRef, {
      width: '60%',
      maxWidth: '700px',
    });
  }

  deleteIntent() {
    this.showSpinner = true;
    this.service.deleteIntent(this.intent.name).subscribe({
      next: () => {
        this.showSpinner = false;
        this.deleteIntentDialogRef!.close();
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['green-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: 'Intent deleted', icon: 'tick-with-circle'},
        });
        this.router.navigateByUrl('/');
      },
      error: () => {
        this.showSpinner = false;
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['red-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {
            text: 'failed to delete intent',
            icon: 'cross-in-circle-white',
          },
        });
      },
    });
  }

  saveForm() {
    if (!this.intentForm.valid || !this.intentForm.controls.questions.valid) {
      this.snackbar.openFromComponent(ToastMessageComponent, {
        panelClass: ['red-toast'],
        verticalPosition: 'top',
        horizontalPosition: 'right',
        duration: 5000,
        data: {
          text: 'There is an error on the intent form',
          icon: 'cross-in-circle-white',
        },
      });
      return;
    }

    this.showSpinner = true;
    this.intent.name = this.intentForm.controls.name.value!;
    this.intent.gcp_bucket = this.intentForm.controls.gcp_bucket.value!;
    this.intent.prompt = this.intentForm.controls.prompt.value!;
    this.intent.ai_model = this.intentForm.controls.ai_model.value!;
    this.intent.ai_temperature = this.intentForm.controls.ai_temperature.value!;
    this.intent.questions = this.intentForm.controls.questions
      .value as string[];

    this.service.updateIntent(this.intent).subscribe({
      next: () => {
        this.showSpinner = false;
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['green-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: 'Intent Saved', icon: 'tick-with-circle'},
        });
      },
      error: () => {
        this.showSpinner = false;
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ['red-toast'],
          verticalPosition: 'top',
          horizontalPosition: 'right',
          duration: 5000,
          data: {text: 'failed to save intent', icon: 'cross-in-circle-white'},
        });
      },
    });
  }
}
