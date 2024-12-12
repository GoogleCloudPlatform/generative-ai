import { Component } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import {
  MatDialogRef,
} from '@angular/material/dialog';
import { Router } from '@angular/router';
import { ConfigurationService } from 'src/app/services/configuration.service';
import { UserService } from 'src/app/services/user/user.service';

@Component({
  selector: 'app-add-agent-builder',
  templateUrl: './add-agent-builder.component.html',
  styleUrls: ['./add-agent-builder.component.scss'],
})
export class AddAgentBuilderComponent {

  showSpinner = false;
  agentBuilderForm = new FormGroup({
    url: new FormControl<string>('', Validators.required),
  });

  constructor(   
    private dialogRef: MatDialogRef<AddAgentBuilderComponent>,
    private readonly router: Router,
    private readonly configService: ConfigurationService,
    private userService: UserService,
    ){

    }

    saveForm() {
      if(this.agentBuilderForm.valid){
        this.userService.showLoading();
        this.configService.addConfiguration(this.agentBuilderForm.get('url')?.value!).subscribe({
          next: ()=>{
            this.userService.hideLoading();
            this.dialogRef.close()!;
            this.router.navigateByUrl('/');
          },
          error: ()=>{
            this.userService.hideLoading();
          }
        });
      }
    }

}
