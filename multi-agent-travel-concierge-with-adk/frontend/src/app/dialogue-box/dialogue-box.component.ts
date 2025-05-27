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
