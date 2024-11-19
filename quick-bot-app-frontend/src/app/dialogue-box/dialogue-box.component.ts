import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';


@Component({
  selector: 'app-dialogue-box',
  templateUrl: './dialogue-box.component.html',
  styleUrls: ['./dialogue-box.component.scss']
})
export class DialogueBoxComponent {
  data: any;

  constructor(
    private dialogRef: MatDialogRef<DialogueBoxComponent>,
    @Inject(MAT_DIALOG_DATA) data: { title: string,
    icon: string,
    description: string,
    cancelBtnText?: string,
    showConfirmBtn?:boolean,
    cancelCallBackFunction?: ()=>{},
    confirmBtnText?: string,
    confirmCallBackFunction?: ()=>{},
    needsExtraProcessing: boolean,
    extraProcessingFunction?: ()=>{}
  }
  ) {
    this.data = data;
    if(this.data.needsExtraProcessing){
      this.data?.extraProcessingFunction();
    }

  }

  getCallBackFunction( callback : ()=>{} | undefined){
    
    let returnFunction = ()=>{this.dialogRef.close()};
    if(typeof callback === "function"){
      returnFunction = ()=>{callback();this.dialogRef.close()};
    }
    return returnFunction();

  }

}
