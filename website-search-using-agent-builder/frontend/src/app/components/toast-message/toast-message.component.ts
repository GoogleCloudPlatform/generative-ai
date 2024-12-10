import { Component, Inject,ViewEncapsulation } from '@angular/core';
import {MatSnackBar, MAT_SNACK_BAR_DATA } from '@angular/material/snack-bar';

@Component({
  selector: 'app-toast-message',
  templateUrl: './toast-message.component.html',
  styleUrls: ['./toast-message.component.scss'],
  encapsulation: ViewEncapsulation.None,
})
export class ToastMessageComponent {

  text: string
  icon: string
  constructor(
    private _snackBar: MatSnackBar,
    @Inject(MAT_SNACK_BAR_DATA) public snackBarData: any
  ) {
    this.text = snackBarData.text
    this.icon = snackBarData.icon
  }

  closeToast() {
    this._snackBar.dismiss()
  }

}
