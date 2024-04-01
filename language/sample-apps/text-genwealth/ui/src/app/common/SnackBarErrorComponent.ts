import {Component} from '@angular/core';
import {MatSnackBar, MatSnackBarModule} from '@angular/material/snack-bar';

/**
 * @title Show error message in snackbar
 */
@Component({
  selector: 'app-error',
  template: '<div></div>',
  standalone: true,
  imports: [
    MatSnackBarModule
  ],
})
export class SnackBarErrorComponent {
  error?: string = undefined;

  constructor(private snackBar: MatSnackBar) {}

  showError(message: string, error: any) {
    this.snackBar.open('ERROR: ' + message, 'Close', {
        panelClass: 'snackbar-error'
    });
    console.error(message, error);
  }
}