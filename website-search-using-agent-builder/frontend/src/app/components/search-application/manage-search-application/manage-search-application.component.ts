import { Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { SearchApplicationService } from 'src/app/services/search_application.service';
import { ReplaySubject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { UserService } from 'src/app/services/user/user.service';
import { Router } from '@angular/router';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-manage-search-application',
  templateUrl: './manage-search-application.component.html',
  styleUrls: ['./manage-search-application.component.scss']
})
export class ManageSearchApplicationComponent implements OnDestroy{

  @ViewChild('deleteDialogRef', { static: true })
  deleteDialogRef!: TemplateRef<{}>;
  deleteAgentDialogRef?: MatDialogRef<{}>;

  form = new FormGroup({
    engine_id: new FormControl<string>('', Validators.required),
    region: new FormControl<string>('', Validators.required),
  });
  private readonly destroyed = new ReplaySubject<void>(1);

  constructor(
    private readonly searchApplicationService: SearchApplicationService,
    private readonly userService: UserService,
    private readonly router : Router,
    private dialog: MatDialog,
    ){
    this.disableForm();
    this.getConfigData();
  }

  disableForm(){
    this.form.disable();
  }

  enableForm(){
    this.form.enable();
  }

  getConfigData(){
    this.userService.showLoading();
    this.searchApplicationService.get().pipe(takeUntil(this.destroyed)).subscribe({
      next: (response)=>{
        this.form.controls.engine_id.setValue(response.engine_id);
        this.form.controls.region.setValue(response.region);
        this.userService.hideLoading();
      },
      error: ()=>{
        this.userService.hideLoading();
      }
    });
  }

  saveForm(){
    this.userService.showLoading();
    let searchApplication = {
      engine_id: this.form.controls.engine_id.value!,
      region: this.form.controls.region.value!,
    }

    this.searchApplicationService.update(searchApplication).subscribe({
      next: ()=>{
        this.userService.hideLoading();
        this.disableForm();
      },
      error: ()=>{
        this.userService.hideLoading();
      }
    });
  }

  showDeleteDialog(){
    this.deleteAgentDialogRef = this.dialog.open(this.deleteDialogRef, { width: '60%', maxWidth: '700px' });

  }

  deleteConfig(){
    this.userService.showLoading();

    let searchApplication = {
      engine_id: this.form.controls.engine_id.value!,
      region: this.form.controls.region.value!,
    }

    this.searchApplicationService.delete(searchApplication).subscribe({
      next: ()=>{
        this.userService.hideLoading();
        this.deleteAgentDialogRef?.close();
        this.router.navigateByUrl('/');
      },
      error: ()=>{
        this.userService.hideLoading();
      }
    });
  }

  navigateToMain(){
    this.router.navigateByUrl('/');
  }

  ngOnDestroy(): void {
    this.destroyed.next();
    this.destroyed.complete();
  }
}
