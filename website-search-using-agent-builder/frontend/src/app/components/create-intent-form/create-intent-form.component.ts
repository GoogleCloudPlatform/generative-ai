import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import { IntentDetails, IntentService, Model } from 'src/app/services/intent.service';
import { ToastMessageComponent } from '../shared/toast-message/toast-message.component';
import { MatSnackBar } from '@angular/material/snack-bar';
import {
  MatDialogRef,
} from '@angular/material/dialog';
import { Router } from '@angular/router';
import { ModelsService } from 'src/app/services/models.service';

@Component({
  selector: 'app-create-intent-form',
  templateUrl: './create-intent-form.component.html',
  styleUrls: ['./create-intent-form.component.scss'],
  providers: [     {
    provide: MatDialogRef,
    useValue: {}
  }],
})
export class CreateIntentFormComponent {

  @Output() discardFormCreation: EventEmitter<boolean> = new EventEmitter()

  models: Model[] = [];
  showSpinner = false;

  intentForm = new FormGroup({
    name: new FormControl<string>('', Validators.required),
  })

  constructor(
    private snackbar: MatSnackBar,
    private service: IntentService,
    private readonly dialogRef: MatDialogRef<CreateIntentFormComponent>,
    private readonly router: Router,
    private readonly modelsService: ModelsService,
  ) {
    this.modelsService.getAll().subscribe(response => {
      this.models = response;
    });
  }

  discardForm() {
    this.discardFormCreation.emit()
  }

  saveForm() {
    if (!this.intentForm.valid){
      this.snackbar.openFromComponent(ToastMessageComponent, {
        panelClass: ["red-toast"],
        verticalPosition: "top",
        horizontalPosition: "right",
        duration: 5000,
        data: { text: 'There is an error on the intent creation form', icon: "cross-in-circle-white" },
      });
      return;
    };

    let intent: IntentDetails = {
      name: this.intentForm.controls.name.value!,
      status: "1",
    }
    this.showSpinner = true;
    this.service.saveIntent(intent).subscribe({
      next: () => {
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ["green-toast"],
          verticalPosition: "top",
          horizontalPosition: "right",
          duration: 5000,
          data: { text: 'Intent Saved', icon: "tick-with-circle" },
        });
        this.showSpinner = false;
        this.router.navigateByUrl('/');
      },
      error: (response) => {
        this.showSpinner = false;
        const message = response.error && response.error.detail ? response.error.detail : "Error creating intent"
        this.snackbar.openFromComponent(ToastMessageComponent, {
          panelClass: ["red-toast"],
          verticalPosition: "top",
          horizontalPosition: "right",
          duration: 5000,
          data: { text: message, icon: "cross-in-circle-white" },
        });

      }
    })
  }

}
