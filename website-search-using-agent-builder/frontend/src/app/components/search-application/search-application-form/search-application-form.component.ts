import { Component } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import {
  MatDialogRef,
} from '@angular/material/dialog';
import { Router } from '@angular/router';
import { SearchApplicationService } from 'src/app/services/search_application.service';
import { UserService } from 'src/app/services/user/user.service';

@Component({
  selector: 'app-search-application-form',
  templateUrl: './search-application-form.component.html',
  styleUrls: ['./search-application-form.component.scss'],
})
export class SearchApplicationFormComponent {

  showSpinner = false;
  form = new FormGroup({
    engine_id: new FormControl<string>('', Validators.required),
    region: new FormControl<string>('', Validators.required),
  });

  constructor(
    private dialogRef: MatDialogRef<SearchApplicationFormComponent>,
    private readonly router: Router,
    private readonly searchApplicationService: SearchApplicationService,
    private userService: UserService,
    ){

    }

    saveForm() {
      if(this.form.valid){
        let searchApplication = {
          engine_id: this.form.controls.engine_id.value!,
          region: this.form.controls.region.value!
        }
        this.userService.showLoading();
        this.searchApplicationService.create(searchApplication).subscribe({
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
