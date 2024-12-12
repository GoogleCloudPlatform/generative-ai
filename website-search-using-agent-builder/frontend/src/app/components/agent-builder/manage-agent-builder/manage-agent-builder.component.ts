import { Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import { ConfigurationService } from 'src/app/services/configuration.service';
import { ReplaySubject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { UserService } from 'src/app/services/user/user.service';
import { Router } from '@angular/router';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-manage-agent-builder',
  templateUrl: './manage-agent-builder.component.html',
  styleUrls: ['./manage-agent-builder.component.scss']
})
export class ManageAgentBuilderComponent implements OnDestroy{

  @ViewChild('deleteDialogRef', { static: true })
  deleteDialogRef!: TemplateRef<{}>;
  deleteAgentDialogRef?: MatDialogRef<{}>;

  disableBuilderForm = true;
  agentBuilderForm = new FormGroup({
    url: new FormControl<string>('', Validators.required),
  });
  private readonly destroyed = new ReplaySubject<void>(1);

  constructor(private readonly configService: ConfigurationService, 
    private readonly userService: UserService, 
    private readonly router : Router,
    private dialog: MatDialog,
    ){
    this.agentBuilderForm.controls.url.disable();
    this.getConfigData();
  }

  enableForm(){
    this.disableBuilderForm = false;
    this.agentBuilderForm.controls.url.enable();
  }

  disableForm(){
    this.disableBuilderForm = true;
    this.agentBuilderForm.controls.url.disable();
  }

  getConfigData(){
    this.userService.showLoading();
    this.configService.getConfiguration().pipe(takeUntil(this.destroyed)).subscribe({
      next: (response)=>{
        if(response[0].url) this.agentBuilderForm.controls.url.setValue(response[0].url);
        this.userService.hideLoading();
      },
      error: ()=>{
        this.userService.hideLoading();
      }
    });
  }

  saveForm(){
    this.userService.showLoading();
    this.configService.updateConfig(this.agentBuilderForm.controls.url.value!).subscribe({
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
    this.configService.deleteConfiguration().subscribe({
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
