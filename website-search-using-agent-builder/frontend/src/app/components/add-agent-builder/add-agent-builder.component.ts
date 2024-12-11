import { Component } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import {
  MatDialogRef,
} from '@angular/material/dialog';
import { Router } from '@angular/router';
import { SearchService } from 'src/app/services/search.service';

@Component({
  selector: 'app-add-agent-builder',
  templateUrl: './add-agent-builder.component.html',
  styleUrls: ['./add-agent-builder.component.scss'],
  providers: [     {
    provide: MatDialogRef,
    useValue: {}
  }],
})
export class AddAgentBuilderComponent {

  showSpinner = false;
  agentBuilderForm = new FormGroup({
    name: new FormControl<string>('', Validators.required),
  });

  constructor(   
    private readonly dialogRef: MatDialogRef<AddAgentBuilderComponent>,
    private readonly router: Router,
    private readonly service: SearchService){

    }

    saveForm() {
  
    }

}
